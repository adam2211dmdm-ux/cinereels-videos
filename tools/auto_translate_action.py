#!/usr/bin/env python3
"""CineReels auto-translate — GitHub Actions half (runs inside the repo).

This is the end-to-end version of the local watcher
(~/workspace/your_files/cinereels/tools/auto_translate.py). It runs on a
GitHub-hosted runner with NO human approval: it transcribes, detects
burned-in subtitles, translates EN<->AR, writes .vtt files, updates
videos.json, and leaves the commit+push to the workflow step (GITHUB_TOKEN).

Ported logic (validated 2026-11-23 on the local watcher):
- Candidates: published episodes with a video_url but NO subtitle URLs
  (either language missing) and not flagged burned_subs. Web-page
  episodes are skipped (no direct video to transcribe). Max 8 per run.
- Transcription: faster-whisper `small`, int8, beam_size=1, vad_filter.
  No speech -> skip, mark nothing.
- Burned-in detection: bottom 22% band, PIL luminance threshold 190 +
  tesseract ara+eng --psm 6 TSV; a frame is a HIT when >= 3 words have
  length >= 2 and confidence >= 60; episode is burned_in when >= 2
  sampled frames hit. Frames sampled at midpoints of the first 3 speech
  segments PLUS 3 fixed fractions (0.25/0.5/0.75); real duration from
  ffprobe (manifest durations can be wrong).
- Translation: Argos Translate packages (Helsinki-NLP Opus-MT) run
  directly on CTranslate2 + SentencePiece — offline, CPU, no torch,
  no language token (single-pair models). The .argosmodel zips are
  downloaded from the Argos package index and unzipped by the workflow
  into models-ct2/ (cached between runs); the script reads them from
  $ARGOS_MODELS_DIR (default ./models-ct2).
  Detected ar -> translate to en; detected en -> translate to ar;
  any other detected language -> translate to BOTH en and ar.
- VTT format matches the existing files in subtitles/drama/: WEBVTT
  header + NOTE lines + numbered cues `HH:MM:SS.mmm --> HH:MM:SS.mmm`.
  File name: `<series_id>-episode<N>_<lang>.vtt` (or the basename of an
  already-present subtitle URL for that episode, if one language exists).
- Manifest: ONLY the processed episode's subtitles_en_url /
  subtitles_ar_url / burned_subs fields are touched. Written back
  encrypted: the catalog on disk is videos.enc (base64 single-line
  AES-256-CBC of the JSON, indent=1, raw UTF-8, no trailing newline) —
  decrypt with MANIFEST_KEY / MANIFEST_IV (repo secrets) at start,
  re-encrypt on write. NEVER write a plaintext videos.json. The
  manifest signature (.sig) is RETIRED since app v1.24 — this script
  never reads or writes any .sig file.
- Downloads that fail (e.g. dead CDN links) are skipped WITHOUT marking
  anything, so a later run retries them.
- Writes `.auto-translate-summary.json` (repo root, NOT committed) with
  the changed paths + a commit message for the workflow step. Exit 0
  always unless the manifest itself cannot be read.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import date

from PIL import Image

REPO_ROOT = os.getcwd()
MANIFEST_PATH = os.path.join(REPO_ROOT, "videos.enc")
SUBS_DIR = os.path.join(REPO_ROOT, "subtitles", "drama")
RAW_BASE = ("https://raw.githubusercontent.com/adam2211dmdm-ux/"
            "cinereels-videos/main")
ARGOS_MODELS_DIR = os.environ.get("ARGOS_MODELS_DIR",
                                  os.path.join(REPO_ROOT, "models-ct2"))
WORK = os.environ.get("RUNNER_TEMP", "/tmp") + "/auto_translate_action"
MAX_PER_RUN = 8
os.makedirs(WORK, exist_ok=True)
os.makedirs(SUBS_DIR, exist_ok=True)


def run(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ---------------------------------------------------------------- manifest crypto
# v1.48: the catalog on disk is videos.enc (base64 single-line AES-256-CBC).
# Key/IV come from the MANIFEST_KEY / MANIFEST_IV env vars (repo secrets).
# openssl does the cipher — no extra pip dependency on the runner.

def manifest_crypto():
    """(key_hex, iv_hex) from env. Raises RuntimeError when missing."""
    key = os.environ.get("MANIFEST_KEY", "")
    iv = os.environ.get("MANIFEST_IV", "")
    if len(key) != 64 or len(iv) != 32:
        raise RuntimeError("MANIFEST_KEY/IV missing or wrong length "
                           "(need 64/32 hex chars)")
    return key, iv


def load_manifest():
    """Decrypt videos.enc -> parsed manifest dict."""
    key, iv = manifest_crypto()
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        raw = base64.b64decode(f.read().strip())
    r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc",
                        "-K", key, "-iv", iv],
                       input=raw, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("manifest decrypt failed (openssl exit %d)"
                           % r.returncode)
    return json.loads(r.stdout.decode("utf-8"))


def save_manifest(manifest):
    """Serialize (indent=1, no trailing newline) -> encrypt -> videos.enc."""
    key, iv = manifest_crypto()
    text = json.dumps(manifest, ensure_ascii=False, indent=1)
    r = subprocess.run(["openssl", "enc", "-aes-256-cbc",
                        "-K", key, "-iv", iv],
                       input=text.encode("utf-8"), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("manifest encrypt failed (openssl exit %d)"
                           % r.returncode)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        f.write(base64.b64encode(r.stdout).decode("ascii") + "\n")


def fmt_time(sec):
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return "%02d:%02d:%06.3f" % (h, m, s)


def _good_words(tsv_out):
    """Count tesseract TSV words with length >= 2 and confidence >= 60."""
    n, words = 0, []
    for ln in tsv_out.strip().split("\n")[1:]:
        f = ln.split("\t")
        if len(f) >= 12 and f[11].strip():
            try:
                conf = float(f[10])
            except ValueError:
                continue
            w = f[11].strip()
            if len(w) >= 2 and conf >= 60:
                n += 1
                words.append(w)
    return n, words


def ocr_bottom_band(mp4, duration, speech_times=None):
    """Detect burned-in subs in the bottom 22% band. Returns (hits, total)."""
    times = []
    for t in (speech_times or [])[:3]:
        times.append(float(t))
    for frac in (0.25, 0.5, 0.75):
        times.append(max(1.0, duration * frac))
    times = sorted(set(round(t, 1) for t in times))
    dedup = []
    for t in times:
        if not dedup or t - dedup[-1] >= 1.5:
            dedup.append(t)
    hits = 0
    for t in dedup[:6]:
        tag = "t%.1f" % t
        frame = os.path.join(WORK, "frame_%s.png" % tag)
        band = os.path.join(WORK, "band_%s.png" % tag)
        thr = os.path.join(WORK, "band_%s_thr.png" % tag)
        r = run(["ffmpeg", "-y", "-v", "error", "-i", mp4, "-ss", str(t),
                 "-frames:v", "1", frame], timeout=180)
        if r.returncode != 0:
            continue
        r = run(["ffmpeg", "-y", "-v", "error", "-i", frame,
                 "-vf", "crop=iw:ih*0.22:0:ih*0.78,scale=iw*2:ih*2", band])
        if r.returncode != 0:
            continue
        try:
            Image.open(band).convert("L").point(
                lambda p: 255 if p > 190 else 0).save(thr)
        except Exception:
            continue
        r = run(["tesseract", thr, "stdout", "-l", "ara+eng", "--psm", "6",
                 "tsv"], timeout=120)
        n, _words = _good_words(r.stdout)
        if n >= 3:
            hits += 1
    return hits, len(dedup[:6])


def cleanup(ep_id, keep_json=False):
    for name in os.listdir(WORK):
        if not name.startswith(ep_id):
            continue
        if name.endswith(".json") and keep_json:
            continue
        try:
            os.remove(os.path.join(WORK, name))
        except OSError:
            pass
    for f in [os.path.join(WORK, x) for x in os.listdir(WORK)
              if x.startswith(("frame_", "band_"))]:
        try:
            os.remove(f)
        except OSError:
            pass


def transcribe(mp4, ep_id):
    """Extract 16k mono wav, transcribe with faster-whisper small."""
    wav = os.path.join(WORK, ep_id + ".wav")
    r = run(["ffmpeg", "-y", "-v", "error", "-i", mp4,
             "-ac", "1", "-ar", "16000", "-sample_fmt", "s16", wav])
    if r.returncode != 0:
        return None, "ffmpeg audio extract failed: " + r.stderr[:300]
    code = (
        "import json, wave, numpy as np\n"
        "from faster_whisper import WhisperModel\n"
        "w = wave.open(%r, 'rb')\n"
        "audio = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0\n"
        "model = WhisperModel('small', device='cpu', compute_type='int8')\n"
        "segs, info = model.transcribe(audio, language=None, beam_size=1, vad_filter=True)\n"
        "out = [{'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip()} for s in segs]\n"
        "json.dump({'language': info.language, 'segments': out}, open(%r, 'w'), ensure_ascii=False)\n"
        "print('LANG', info.language, 'SEGS', len(out))\n"
    ) % (wav, os.path.join(WORK, ep_id + ".json"))
    r = run([sys.executable, "-c", code], timeout=1500)
    if r.returncode != 0:
        return None, "whisper failed: " + (r.stderr or r.stdout)[-500:]
    data = json.load(open(os.path.join(WORK, ep_id + ".json")))
    return data, None


class ArgosTranslator:
    """Argos Translate packages (Helsinki-NLP Opus-MT) via CTranslate2.

    Each package dir holds sentencepiece.model + model/model.bin
    (single-pair models — no language token is needed). Packages are the
    .argosmodel zips from the Argos package index, downloaded + unzipped
    by the workflow into models-ct2/ (cached between runs). Translators
    are loaded lazily once per direction and reused. Inference mirrors
    argostranslate.translate.apply_packaged_translation: SentencePiece
    encode, translate_batch (beam 4, length penalty 0.2), decode.
    """

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self._cache = {}

    def _find_pkg(self, src, dst):
        for cand in ("translate-%s_%s/%s_%s" % (src, dst, src, dst),
                     "%s_%s/%s_%s" % (src, dst, src, dst),
                     "%s_%s" % (src, dst)):
            p = os.path.join(self.base_dir, cand)
            if (os.path.exists(os.path.join(p, "sentencepiece.model"))
                    and os.path.exists(
                        os.path.join(p, "model", "model.bin"))):
                return p
        raise RuntimeError("Argos model for %s -> %s not found under %s"
                           % (src, dst, self.base_dir))

    def _load(self, src, dst):
        import ctranslate2
        import sentencepiece as spm
        pkg = self._find_pkg(src, dst)
        sp = spm.SentencePieceProcessor(
            model_file=os.path.join(pkg, "sentencepiece.model"))
        tr = ctranslate2.Translator(os.path.join(pkg, "model"),
                                    device="cpu")
        self._cache[(src, dst)] = (tr, sp)
        return self._cache[(src, dst)]

    def translate(self, texts, src, dst):
        if (src, dst) not in self._cache:
            self._load(src, dst)
        tr, sp = self._cache[(src, dst)]
        encoded = [sp.encode(t, out_type=str) if t.strip() else []
                   for t in texts]
        results = tr.translate_batch(
            encoded, beam_size=4, length_penalty=0.2,
            replace_unknowns=True)
        return [sp.decode(r.hypotheses[0]).strip() if t.strip() else ""
                for r, t in zip(results, texts)]


_TRANSLATOR = None


def translate_segments(segments, src, dst):
    """Translate a list of {start, end, text} with Opus-MT (batched)."""
    global _TRANSLATOR
    if _TRANSLATOR is None:
        _TRANSLATOR = ArgosTranslator(ARGOS_MODELS_DIR)
    texts = [s["text"] for s in segments]
    out_texts = _TRANSLATOR.translate(texts, src, dst)
    return [{"start": s["start"], "end": s["end"], "text": t}
            for s, t in zip(segments, out_texts)]


def write_vtt(path, series_title, ep_num, lang_name, lang_code,
              segments, translated):
    today = date.today().isoformat()
    if translated:
        note2 = ("Translated %s from the real episode audio "
                 "(faster-whisper small + Opus-MT)." % today)
    else:
        note2 = ("Transcribed %s from the real episode audio "
                 "(faster-whisper small)." % today)
    lines = ["WEBVTT", "",
             "NOTE CineReels — %s — Episode %d — %s subtitles"
             % (series_title, ep_num, lang_name),
             "NOTE " + note2, ""]
    for i, s in enumerate(segments, 1):
        lines.append(str(i))
        lines.append("%s --> %s" % (fmt_time(s["start"]), fmt_time(s["end"])))
        lines.append(s["text"])
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def vtt_basename(video, lang):
    """File name for a subtitle file, matching the existing convention.

    If this episode already has one subtitle URL, reuse its basename
    (swap _en/_ar). Otherwise <series_id>-episode<N>_<lang>.vtt.
    """
    for key in ("subtitles_en_url", "subtitles_ar_url"):
        url = video.get(key)
        if url:
            base = url.rsplit("/", 1)[-1]
            if base.endswith("_en.vtt"):
                base = base[:-7]
            elif base.endswith("_ar.vtt"):
                base = base[:-7]
            return "%s_%s.vtt" % (base, lang)
    return "%s-episode%d_%s.vtt" % (video["series_id"],
                                    video.get("episode_number", 0), lang)


def main():
    try:
        manifest = load_manifest()
    except Exception as e:
        print(json.dumps({"error": "manifest read failed: %s" % e}))
        return 1
    series_titles = {}
    for s in manifest.get("series", []):
        series_titles[s["id"]] = {
            "ar": s.get("title_ar") or s.get("id"),
            "en": s.get("title_en") or s.get("title_ar") or s.get("id"),
        }
    cands = []
    for v in manifest.get("videos", []):
        if v.get("status") != "published":
            continue
        if not v.get("video_url"):
            continue
        if v.get("burned_subs"):
            continue
        if v.get("web_page"):
            continue
        if v.get("subtitles_en_url") and v.get("subtitles_ar_url"):
            continue
        cands.append(v)
    summary = {"candidates": len(cands), "actions": [],
               "changed_paths": [], "commit_message": ""}
    changed = False
    msgs = []
    done = 0
    for v in cands:
        if done >= MAX_PER_RUN:
            break
        ep_id = v["id"]
        num = v.get("episode_number", 0)
        titles = series_titles.get(v["series_id"], {"ar": v["series_id"],
                                                    "en": v["series_id"]})
        mp4 = os.path.join(WORK, ep_id + ".mp4")
        url = v["video_url"]
        if url.lower().split("?")[0].endswith(".m3u8"):
            r = run(["ffmpeg", "-y", "-v", "error", "-i", url,
                     "-c", "copy", "-bsf:a", "aac_adtstoasc", mp4],
                    timeout=900)
            if r.returncode != 0:
                print("SKIP %s: HLS download failed" % ep_id)
                cleanup(ep_id)
                continue
        else:
            try:
                urllib.request.urlretrieve(url, mp4)
            except Exception as e:
                print("SKIP %s: download failed: %s" % (ep_id, e))
                cleanup(ep_id)
                continue
        dur = v.get("duration_sec") or 60
        r = run(["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of",
                 "default=noprint_wrappers=1:nokey=1", mp4], timeout=60)
        try:
            dur = float(r.stdout.strip())
        except (ValueError, AttributeError):
            pass
        data, err = transcribe(mp4, ep_id)
        if err:
            print("SKIP %s: %s" % (ep_id, err))
            cleanup(ep_id)
            continue
        if not data["segments"]:
            print("SKIP %s: no speech" % ep_id)
            cleanup(ep_id)
            continue
        midpoints = [(s["start"] + s["end"]) / 2.0
                     for s in data["segments"][:3]]
        hits, nframes = ocr_bottom_band(mp4, dur, midpoints)
        if hits >= 2:
            v["burned_subs"] = True
            changed = True
            # v1.37: burned-in subs are in the audio language. When the
            # audio is English, the burned text is English — still make
            # an ARABIC subtitle file, so the app can show Arabic over
            # the burned English on its dark box. English needs no file
            # (already in the picture). Arabic audio: the burned text
            # is already Arabic, nothing to add.
            verdict = "burned_in"
            detail = "OCR hits %d/%d frames" % (hits, nframes)
            if data["language"] == "en":
                try:
                    ar_segments = translate_segments(data["segments"],
                                                     "en", "ar")
                except Exception as e:
                    print("SKIP %s: AR translation for burned-in ep failed: %s"
                          % (ep_id, e))
                    ar_segments = None
                if ar_segments:
                    fname = vtt_basename(v, "ar")
                    fpath = os.path.join(SUBS_DIR, fname)
                    write_vtt(fpath, titles["ar"], num, "Arabic", "ar",
                              ar_segments, translated=True)
                    rel = "subtitles/drama/" + fname
                    v["subtitles_ar_url"] = RAW_BASE + "/" + rel
                    if rel not in summary["changed_paths"]:
                        summary["changed_paths"].append(rel)
                    verdict = "burned_in_ar"
                    detail += "; AR vtt added"
                    msgs.append("ep%d burned-in subs, AR added" % num)
                else:
                    msgs.append("ep%d burned-in subs" % num)
            else:
                msgs.append("ep%d burned-in subs" % num)
            summary["actions"].append({"id": ep_id, "episode_number": num,
                                       "verdict": verdict,
                                       "detail": detail})
            done += 1
            print("BURNED_IN %s (%d/%d frames)%s" % (ep_id, hits, nframes,
                  " +AR" if verdict == "burned_in_ar" else ""))
            cleanup(ep_id)
            continue
        lang = data["language"]
        by_lang = {}
        if lang in ("en", "ar"):
            by_lang[lang] = data["segments"]
            other = "ar" if lang == "en" else "en"
            try:
                by_lang[other] = translate_segments(data["segments"],
                                                    lang, other)
            except Exception as e:
                print("SKIP %s: translation %s->%s failed: %s"
                      % (ep_id, lang, other, e))
                cleanup(ep_id)
                continue
        else:
            # Detected language is neither en nor ar: translate to both.
            try:
                by_lang["en"] = translate_segments(data["segments"],
                                                   lang, "en")
                by_lang["ar"] = translate_segments(data["segments"],
                                                   lang, "ar")
            except Exception as e:
                print("SKIP %s: translation from %s failed: %s"
                      % (ep_id, lang, e))
                cleanup(ep_id)
                continue
        for code, lang_name in (("en", "English"), ("ar", "Arabic")):
            fname = vtt_basename(v, code)
            fpath = os.path.join(SUBS_DIR, fname)
            write_vtt(fpath, titles["en"] if code == "en" else titles["ar"],
                      num, lang_name, code, by_lang[code],
                      translated=(code != lang))
            rel = "subtitles/drama/" + fname
            v["subtitles_%s_url" % code] = RAW_BASE + "/" + rel
            if rel not in summary["changed_paths"]:
                summary["changed_paths"].append(rel)
        changed = True
        summary["actions"].append({"id": ep_id, "episode_number": num,
                                   "verdict": "translated",
                                   "language": lang,
                                   "segments": len(data["segments"])})
        msgs.append("ep%d translated (%s, %d segments)"
                    % (num, lang, len(data["segments"])))
        done += 1
        print("DONE %s: %d segments, detected %s"
              % (ep_id, len(data["segments"]), lang))
        cleanup(ep_id)
    if changed:
        save_manifest(manifest)
        if "videos.enc" not in summary["changed_paths"]:
            summary["changed_paths"].insert(0, "videos.enc")
        summary["commit_message"] = (
            "Auto-translate subtitles: " + "; ".join(msgs))
    with open(os.path.join(REPO_ROOT, ".auto-translate-summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
