#!/usr/bin/env python3
"""CineReels auto-thumbnails — GitHub Actions half (runs inside the repo).

Every 6 hours this workflow finds published episodes whose thumbnail is
NOT yet hosted in this repo (provider CDN thumbnails load slowly or not
at all on Adam's phone, so they show as dark blank cards), picks the
best frame of the real episode video with multilingual CLIP, saves it
as thumbnails/<video_id>.jpg in the repo, and points the manifest's
thumbnail_url at the raw.githubusercontent.com copy. No app change is
needed — the app already reads thumbnail_url.

Ported patterns (from tools/auto_translate_action.py, same repo):
- Manifest: read with json.load, written back with indent=1, raw UTF-8,
  no trailing newline. ONLY the processed video's thumbnail_url is
  touched. The manifest signature (.sig) is RETIRED since app v1.24 —
  this script never reads or writes any .sig file.
- Downloads that fail (e.g. dead CDN links — the 14 dead wave-god eps)
  are skipped WITHOUT marking anything, so a later run retries them.
  One bad video never fails the whole run (skip-fix: iterate ALL
  candidates, stop after MAX_PER_RUN successes).
- Writes `.auto-thumbnails-summary.json` (repo root, NOT committed) with
  the changed paths + a commit message for the workflow step. Exit 0
  always unless the manifest itself cannot be read or the CLIP model
  cannot be loaded (run-level failures — no video could be scored).

Candidate rules:
- status == "published", non-empty video_url, NOT web_page (no direct
  video to frame-grab), thumbnail_url host != raw.githubusercontent.com.
- Priority: picsum.photos placeholders first, then provider CDNs
  (manifest order inside each group). NOTE: the 12 picsum videos
  (lm-ep16..25, sc-ep2..3) have NO video_url at all — they are
  unpublished placeholders, so they are skipped (no frames exist) and
  keep their picsum thumbnail until Adam uploads the videos.

Per video:
- Download: HLS (.m3u8) via ffmpeg -c copy (same as the translate
  script); direct mp4 via urllib. Duration from ffprobe (manifest
  durations can be wrong), falling back to duration_sec or 60s.
- Extract 5 candidate frames at 10/30/50/70/90% of duration.
  Near-black frames (mean luminance < 15 via PIL) are skipped.
- Score each remaining frame with multilingual CLIP against the
  SERIES title_ar PLUS description_ar (Arabic, direct): the
  description carries the story, characters and setting, so CLIP
  prefers frames that actually represent the series, not just any
  frame. Description source: the series entry's description_ar first,
  else the video's description_ar; if neither exists, the title alone.
  The description is capped at ~400 chars (title first, so truncation
  never drops it).
  TWO models, one shared 512-dim space (this is how the multilingual
  CLIP is designed — see its README): the TEXT side is
  sentence-transformers/clip-ViT-B-32-multilingual-v1 (a multilingual
  DistilBERT distilled to match CLIP's space — it is TEXT-ONLY, it
  cannot encode images); the IMAGE side is the original
  sentence-transformers/clip-ViT-B-32 (CLIP ViT-B/32). Text embedding
  comes from the first, image embeddings from the second; cosine
  similarity between them picks the best frame.
- Sharpness: frames are also checked for blur (variance of the
  PIL FIND_EDGES response, via numpy). A frame much blurrier than the
  episode's own sharpest frame (under 10% of its sharpness, or under
  an absolute floor) is dropped before scoring; if that would drop
  everything, the sharpest frame is kept.
- Save the best frame as JPEG quality 85 to thumbnails/<video_id>.jpg
  (vertical 540x960 frame kept as-is, never cropped/resized) and set
  thumbnail_url to the raw.githubusercontent.com URL.
- No API keys anywhere. Network use: episode video download + the
  CLIP model download on first use (cached between runs by the
  workflow) only.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from PIL import Image, ImageFilter, ImageStat

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy ships with torch
    np = None

REPO_ROOT = os.getcwd()
MANIFEST_PATH = os.path.join(REPO_ROOT, "videos.json")
THUMBS_DIR = os.path.join(REPO_ROOT, "thumbnails")
RAW_BASE = ("https://raw.githubusercontent.com/adam2211dmdm-ux/"
            "cinereels-videos/main")
WORK = os.environ.get("RUNNER_TEMP", "/tmp") + "/auto_thumbnails_action"
MAX_PER_RUN = 5
# CLIP, two halves of one 512-dim space (see the docstring above):
#  - text: multilingual DistilBERT (TEXT-ONLY — cannot encode images)
#  - image: the original CLIP ViT-B/32 (encodes the frames)
CLIP_TEXT_MODEL = "sentence-transformers/clip-ViT-B-32-multilingual-v1"
CLIP_IMG_MODEL = "sentence-transformers/clip-ViT-B-32"
# Escape hatches: point at local model directories instead of the HF
# Hub ids (e.g. CLIP_TEXT_MODEL_PATH=~/clip-model). Useful when the
# Hub download stalls behind a proxy — curl the model files into dirs
# with the same layout as the repos and set these. The workflow uses
# the Hub ids.
CLIP_TEXT_MODEL_PATH = os.environ.get("CLIP_TEXT_MODEL_PATH",
                                      CLIP_TEXT_MODEL)
CLIP_IMG_MODEL_PATH = os.environ.get("CLIP_IMG_MODEL_PATH",
                                     CLIP_IMG_MODEL)
FRAME_FRACTIONS = (0.10, 0.30, 0.50, 0.70, 0.90)
BLACK_LUMINANCE = 15
# Sharpness (variance of the FIND_EDGES response): drop a frame that
# is much blurrier than the episode's own sharpest frame (under 10%
# of it) or nearly edgeless in absolute terms. Calibrated on real
# episode frames — sharp 540x960 frames score in the hundreds, blurry
# ones in the tens or lower.
SHARP_FLOOR = 20.0
SHARP_KEEP_FRAC = 0.10
# Keep the CLIP text focused: title + the head of the description.
DESC_MAX_CHARS = 400
os.makedirs(WORK, exist_ok=True)
os.makedirs(THUMBS_DIR, exist_ok=True)


def run(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def thumb_host(url):
    if not url or "://" not in url:
        return ""
    return urlparse(url).netloc


_TEXT_MODEL = None
_IMG_MODEL = None
_TEXT_CACHE = {}


def get_text_model():
    """Load the multilingual text encoder lazily."""
    global _TEXT_MODEL
    if _TEXT_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _TEXT_MODEL = SentenceTransformer(CLIP_TEXT_MODEL_PATH)
    return _TEXT_MODEL


def get_img_model():
    """Load the original CLIP image encoder lazily."""
    global _IMG_MODEL
    if _IMG_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _IMG_MODEL = SentenceTransformer(CLIP_IMG_MODEL_PATH)
    return _IMG_MODEL


def text_embedding(model, text):
    """Cached text embedding for one CLIP text (L2-normalized)."""
    if text not in _TEXT_CACHE:
        _TEXT_CACHE[text] = model.encode(
            [text], convert_to_tensor=True,
            normalize_embeddings=True)[0]
    return _TEXT_CACHE[text]


def mean_luminance(path):
    try:
        with Image.open(path) as im:
            return ImageStat.Stat(im.convert("L")).mean[0]
    except Exception:
        return 0.0


def sharpness(path):
    """Blur check: variance of the FIND_EDGES response.

    Sharp frames have strong edges (high variance); blurry or flat
    frames have almost none. Returns None when numpy is unavailable
    or the frame cannot be read (caller treats it as "no opinion").
    """
    if np is None:
        return None
    try:
        with Image.open(path) as im:
            edges = im.convert("L").filter(ImageFilter.FIND_EDGES)
            return float(np.asarray(edges, dtype=np.float64).var())
    except Exception:
        return None


def clip_text_for(series, video):
    """CLIP text: series title + description (story/characters/setting).

    Description source: the series entry's description_ar first, else
    the video's description_ar. Title alone when neither exists.
    """
    title = (series.get("title_ar") or series.get("title_en")
             or series.get("id"))
    desc = (series.get("description_ar")
            or video.get("description_ar") or "").strip()
    if not desc:
        return title
    if len(desc) > DESC_MAX_CHARS:
        desc = desc[:DESC_MAX_CHARS].rsplit(" ", 1)[0]
    return "%s. %s" % (title, desc)


def cleanup(ep_id):
    for name in os.listdir(WORK):
        if not name.startswith(ep_id):
            continue
        try:
            os.remove(os.path.join(WORK, name))
        except OSError:
            pass
    for name in os.listdir(WORK):
        if name.startswith("frame_"):
            try:
                os.remove(os.path.join(WORK, name))
            except OSError:
                pass


def download_video(url, mp4):
    """Download an episode to mp4. Returns None on success, error str.

    Up to 3 attempts — the CDN/proxy drops mid-transfer sometimes
    (e.g. a 10 MB mp4 stopping at 4.6 MB). A 404 fails fast with no
    retry (dead link — a later run retries it anyway).
    """
    last_err = None
    for attempt in (1, 2, 3):
        if url.lower().split("?")[0].endswith(".m3u8"):
            r = run(["ffmpeg", "-y", "-v", "error", "-i", url,
                     "-c", "copy", "-bsf:a", "aac_adtstoasc", mp4],
                    timeout=900)
            if r.returncode == 0:
                last_err = None
                break
            last_err = "HLS download failed: " + (r.stderr or "")[:200]
            if "404" in (r.stderr or ""):
                break
        else:
            try:
                urllib.request.urlretrieve(url, mp4)
                last_err = None
                break
            except urllib.error.HTTPError as e:
                last_err = "download failed: HTTP %s" % e.code
                if e.code == 404:
                    break
            except Exception as e:
                last_err = "download failed: %s" % e
        print("  download attempt %d failed: %s" % (attempt, last_err))
        time.sleep(5)
    if last_err is not None:
        return last_err
    try:
        if os.path.getsize(mp4) == 0:
            return "downloaded file is empty"
    except OSError as e:
        return "downloaded file unreadable: %s" % e
    return None


def probe_duration(mp4, fallback):
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", mp4], timeout=60)
    try:
        dur = float(r.stdout.strip())
        if dur > 0:
            return dur
    except (ValueError, AttributeError):
        pass
    return float(fallback or 60)


def extract_frames(mp4, ep_id, duration):
    """Extract one frame per fraction. Returns [(frac, path), ...]."""
    out = []
    for frac in FRAME_FRACTIONS:
        t = max(0.5, duration * frac)
        path = os.path.join(WORK, "%s_frame_%d.jpg" % (ep_id, int(frac * 100)))
        r = run(["ffmpeg", "-y", "-v", "error", "-i", mp4, "-ss", str(t),
                 "-frames:v", "1", path], timeout=180)
        if r.returncode != 0 or not os.path.exists(path):
            continue
        out.append((frac, path))
    return out


def score_frames(text_model, img_model, text, frames):
    """Score [(frac, path)] with CLIP vs the clip text.

    Text embedding from the multilingual text encoder, image
    embeddings from the original CLIP image encoder (same 512-dim
    space). Returns [(frac, score), ...] for frames that encoded OK,
    or None if a model itself failed (fatal — nothing can be scored).
    """
    images = []
    kept = []
    for frac, path in frames:
        try:
            images.append(Image.open(path).convert("RGB"))
            kept.append(frac)
        except Exception:
            continue
    if not images:
        return []
    try:
        text_emb = text_embedding(text_model, text)
        img_embs = img_model.encode(images, convert_to_tensor=True,
                                    normalize_embeddings=True)
        scores = (img_embs @ text_emb).tolist()
    except Exception as e:
        print("CLIP scoring failed: %s" % e)
        return None
    return [(frac, float(s)) for frac, s in zip(kept, scores)]


def main():
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(json.dumps({"error": "manifest read failed: %s" % e}))
        return 1
    series_by_id = {s["id"]: s for s in manifest.get("series", [])}
    cands = []
    for v in manifest.get("videos", []):
        if v.get("status") != "published":
            continue
        if not v.get("video_url"):
            continue
        if v.get("web_page"):
            continue
        if thumb_host(v.get("thumbnail_url")) == "raw.githubusercontent.com":
            continue
        cands.append(v)
    # Priority: picsum.photos placeholders first, then provider CDNs
    # (stable sort keeps manifest order inside each group).
    cands.sort(key=lambda v: 0
               if thumb_host(v.get("thumbnail_url")) == "picsum.photos"
               else 1)
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
        series = series_by_id.get(v["series_id"], {})
        clip_text = clip_text_for(series, v)
        mp4 = os.path.join(WORK, ep_id + ".mp4")
        err = download_video(v["video_url"], mp4)
        if err:
            print("SKIP %s: %s" % (ep_id, err))
            cleanup(ep_id)
            continue
        dur = probe_duration(mp4, v.get("duration_sec"))
        frames = extract_frames(mp4, ep_id, dur)
        if not frames:
            print("SKIP %s: no frames extracted" % ep_id)
            cleanup(ep_id)
            continue
        # Drop near-black frames before scoring.
        usable = []
        for frac, path in frames:
            lum = mean_luminance(path)
            if lum < BLACK_LUMINANCE:
                print("  %s frame %d%% skipped: near-black (lum %.1f)"
                      % (ep_id, int(frac * 100), lum))
                continue
            usable.append((frac, path))
        if not usable:
            print("SKIP %s: all frames near-black" % ep_id)
            cleanup(ep_id)
            continue
        # Drop very blurry frames: keep a frame when its sharpness is
        # at least the absolute floor and at least 10% of the episode's
        # sharpest frame. Unknown sharpness (numpy missing) keeps the
        # frame. Never drop everything: if all fail, keep the sharpest.
        with_sharp = [(frac, path, sharpness(path))
                      for frac, path in usable]
        known = [s for _, _, s in with_sharp if s is not None]
        sharp_by_frac = {}
        if known:
            cutoff = max(SHARP_FLOOR, SHARP_KEEP_FRAC * max(known))
            kept = [(f, p) for f, p, s in with_sharp
                    if s is None or s >= cutoff]
            for f, _p, s in with_sharp:
                if s is not None and s < cutoff:
                    print("  %s frame %d%% skipped: blurry (sharp %.1f)"
                          % (ep_id, int(f * 100), s))
            if kept:
                usable = kept
            else:
                best = max((t for t in with_sharp if t[2] is not None),
                           key=lambda t: t[2])
                usable = [(best[0], best[1])]
                print("  %s: all frames blurry, kept sharpest %d%%"
                      % (ep_id, int(best[0] * 100)))
            sharp_by_frac = {f: s for f, _p, s in with_sharp
                             if s is not None}
        try:
            text_model = get_text_model()
            img_model = get_img_model()
        except Exception as e:
            print(json.dumps({"error": "CLIP model load failed: %s" % e}))
            summary["error"] = "CLIP model load failed: %s" % e
            with open(os.path.join(REPO_ROOT,
                                   ".auto-thumbnails-summary.json"),
                      "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=1)
            cleanup(ep_id)
            return 1
        scored = score_frames(text_model, img_model, clip_text, usable)
        if scored is None:
            # Model-level failure: nothing can be scored, fail the run.
            summary["error"] = "CLIP scoring failed"
            with open(os.path.join(REPO_ROOT,
                                   ".auto-thumbnails-summary.json"),
                      "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=1)
            cleanup(ep_id)
            return 1
        if not scored:
            print("SKIP %s: no frames encoded" % ep_id)
            cleanup(ep_id)
            continue
        best_frac, best_score = max(scored, key=lambda fs: fs[1])
        best_path = dict(usable)[best_frac]
        out_name = "%s.jpg" % ep_id
        out_path = os.path.join(THUMBS_DIR, out_name)
        try:
            with Image.open(best_path) as im:
                im.convert("RGB").save(out_path, "JPEG", quality=85)
        except Exception as e:
            print("SKIP %s: JPEG save failed: %s" % (ep_id, e))
            cleanup(ep_id)
            continue
        rel = "thumbnails/" + out_name
        v["thumbnail_url"] = RAW_BASE + "/" + rel
        changed = True
        if rel not in summary["changed_paths"]:
            summary["changed_paths"].append(rel)
        detail = "best %d%% score %.3f (frames %s)" % (
            int(best_frac * 100), best_score,
            "/".join("%d%%:%.3f/sharp %s" % (
                int(f * 100), s,
                ("%.1f" % sharp_by_frac[f]) if f in sharp_by_frac
                else "?") for f, s in scored))
        summary["actions"].append({"id": ep_id, "episode_number": num,
                                   "verdict": "thumbnail",
                                   "clip_text": clip_text,
                                   "detail": detail})
        print("  %s CLIP text: %s" % (ep_id, clip_text))
        msgs.append("%s ep%d thumbnail" % (v["series_id"], num))
        done += 1
        print("DONE %s: %s" % (ep_id, detail))
        cleanup(ep_id)
    if changed:
        with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        if "videos.json" not in summary["changed_paths"]:
            summary["changed_paths"].insert(0, "videos.json")
        summary["commit_message"] = (
            "Auto-thumbnails: " + "; ".join(msgs))
    with open(os.path.join(REPO_ROOT, ".auto-thumbnails-summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
