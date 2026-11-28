#!/usr/bin/env python3
"""CineReels auto-register own videos — GitHub Actions half.

Adam's OWN videos (made by him or by another AI for him) are plain mp4
files, NOT encrypted — only the catalog (videos.enc) is. He uploads a
new episode mp4 into the repo's videos/ folder (GitHub web upload from
his phone), and this workflow registers it in the encrypted catalog so
it appears in the app for everyone — no Muse involvement.

Filename convention (in videos/):
  <series_id>-episode<N>.mp4   e.g. last-message-episode16.mp4
  episode<N>.mp4               legacy, means last-message
Which series an episode belongs to is read from the FILENAME alone:
the <series_id> part must name a series that already exists in the
manifest and is one of Adam's own-uploaded series — either it has at
least one existing video hosted in the repo (video_url under
RAW_BASE), or it is last-message / second-chance. Provider and
imported series (prov-*, narto-*, ia-*, rs-*, ...) are never accepted
(their videos live on provider hosts, not in the repo), and neither
are slugs with no series in the manifest. Any other file is ignored
with a log line. Video ids keep the short prefix for the two original
series (lm-ep16, sc-ep2); any other own series uses its full slug
(<slug>-ep<N>).

Behavior (idempotent — a full scan every run, safe to re-run):
- For each matching mp4, find the video entry for (series_id,
  episode_number). If it exists as a coming_soon placeholder (empty
  video_url) it is UPDATED in place (video_url, status published,
  coming_soon false, thumbnail -> the series cover so the manifest's
  same-origin check passes, duration from ffprobe). If no entry
  exists, a NEW one is created (title from the series title + Ep N,
  category from the series, language en, subtitle_default ar).
- If the entry is already published with a video_url, it is skipped
  (re-uploading the same file never duplicates anything).
- series.episode_ids is de-duplicated (the manifest once held sc-ep2
  twice) and the episode id is present exactly once.
- Subtitles are NOT made here: committing videos.enc triggers the
  auto-translate workflow, which transcribes + translates the new
  episode (any language -> Arabic via the English pivot) on its own.

Manifest crypto mirrors tools/auto_translate_action.py: videos.enc is
base64 single-line AES-256-CBC, key/IV from MANIFEST_KEY / MANIFEST_IV
repo secrets. NEVER write a plaintext videos.json.
Writes .auto-register-summary.json (repo root, NOT committed) with the
changed paths + a commit message for the workflow step. Exit 0 always
unless the manifest itself cannot be read.
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.parse

REPO_ROOT = os.getcwd()
MANIFEST_PATH = os.path.join(REPO_ROOT, "videos.enc")
VIDEOS_DIR = os.path.join(REPO_ROOT, "videos")
RAW_BASE = ("https://raw.githubusercontent.com/adam2211dmdm-ux/"
            "cinereels-videos/main")

# Short video-id prefixes for the two original own series
# (lm-ep16, sc-ep2). Any other own series uses its full slug
# as the prefix (<slug>-ep<N>).
LEGACY_PREFIX = {"last-message": "lm", "second-chance": "sc"}
PATTERNS = [
    (re.compile(r"^([a-z0-9-]+)-episode(\d+)\.mp4$"),
     lambda m: (m.group(1), int(m.group(2)))),
    (re.compile(r"^episode(\d+)\.mp4$"),
     lambda m: ("last-message", int(m.group(1)))),
]


def is_own_series(sid, series, videos):
    """True when `sid` names one of Adam's own-uploaded series: the
    series must exist in the manifest, must not be a provider series
    (prov-*), and must either be one of the two original own series
    or already have at least one video hosted in the repo (video_url
    under RAW_BASE). Provider/imported series keep their videos on
    provider hosts, so they can never pass this check."""
    if sid not in series:
        return False
    if sid.startswith("prov-"):
        return False
    if sid in LEGACY_PREFIX:
        return True
    return any(v.get("series_id") == sid
               and (v.get("video_url") or "").startswith(RAW_BASE)
               for v in videos)


def run(cmd, timeout=120):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ---------------------------------------------------------------- manifest crypto
# Same scheme as auto_translate_action.py (v1.48). Key/IV from env.

def manifest_crypto():
    key = os.environ.get("MANIFEST_KEY", "")
    iv = os.environ.get("MANIFEST_IV", "")
    if len(key) != 64 or len(iv) != 32:
        raise RuntimeError("MANIFEST_KEY/IV missing or wrong length "
                           "(need 64/32 hex chars)")
    return key, iv


def load_manifest():
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


def match_file(fname):
    for pat, fn in PATTERNS:
        m = pat.match(fname)
        if m:
            return fn(m)
    return None


def probe_duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of",
             "default=noprint_wrappers=1:nokey=1", path], timeout=120)
    try:
        return int(float(r.stdout.strip()))
    except (ValueError, AttributeError):
        return None


def dedupe_ids(ids, keep):
    seen, out = set(), []
    for x in ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    if keep not in seen:
        out.append(keep)
    return out


def safe_thumb(series):
    """Thumbnail for a newly published episode. The manifest's
    same-origin check rejects a PUBLISHED video whose thumbnail_url is
    on a foreign host — second-chance's cover is a picsum URL, so only
    a same-origin cover may be used; otherwise "" (the app falls back
    to the series cover, and the check skips empty strings)."""
    cover = series.get("cover_url") or ""
    if cover.startswith(RAW_BASE):
        return cover
    return ""


def main():
    try:
        manifest = load_manifest()
    except Exception as e:
        print(json.dumps({"error": "manifest read failed: %s" % e}))
        return 1
    series = {s["id"]: s for s in manifest.get("series", [])}
    videos = manifest.get("videos", [])
    by_key = {(v.get("series_id"), v.get("episode_number")): v
              for v in videos}
    summary = {"actions": [], "changed_paths": [], "commit_message": ""}
    changed = False
    msgs = []
    if not os.path.isdir(VIDEOS_DIR):
        print("no videos/ directory, nothing to do")
        return 0
    for fname in sorted(os.listdir(VIDEOS_DIR)):
        m = match_file(fname)
        if not m:
            continue
        sid, num = m
        if not is_own_series(sid, series, videos):
            print("SKIP %s: series %s is not an own series" % (fname, sid))
            continue
        s = series[sid]
        vid = "%s-ep%d" % (LEGACY_PREFIX.get(sid, sid), num)
        url = RAW_BASE + "/videos/" + urllib.parse.quote(fname)
        v = by_key.get((sid, num))
        if v and v.get("video_url") and v.get("status") == "published":
            continue  # already live — never duplicate
        dur = probe_duration(os.path.join(VIDEOS_DIR, fname))
        if v:
            v["video_url"] = url
            v["status"] = "published"
            v["coming_soon"] = False
            v["thumbnail_url"] = safe_thumb(s)
            if dur:
                v["duration_sec"] = dur
            s["episode_ids"] = dedupe_ids(s.get("episode_ids", []), vid)
            msgs.append("%s ep%d published" % (sid, num))
        else:
            cat = s.get("category_id") or "drama"
            title_en = s.get("title_en") or s.get("title_ar") or sid
            title_ar = s.get("title_ar") or s.get("title_en") or sid
            new_v = {
                "id": vid,
                "series_id": sid,
                "episode_number": num,
                "title_en": "%s — Ep %d" % (title_en, num),
                "title_ar": "%s — الحلقة %d" % (title_ar, num),
                "description_en": "",
                "description_ar": "",
                "category": cat,
                "duration_sec": dur or 60,
                "video_url": url,
                "thumbnail_url": safe_thumb(s),
                "subtitles_en_url": None,
                "subtitles_ar_url": None,
                "language": "en",
                "subtitle_default": "ar",
                "likes_count": 0,
                "views_count": 0,
                "is_published": True,
                "tags": [cat],
                "is_locked": False,
                "status": "published",
                "coming_soon": False,
                "views": 0,
            }
            videos.append(new_v)
            by_key[(sid, num)] = new_v
            s["episode_ids"] = dedupe_ids(s.get("episode_ids", []), vid)
            msgs.append("%s ep%d published (new entry)" % (sid, num))
        changed = True
        summary["actions"].append({"file": fname, "series": sid,
                                   "episode_number": num, "video_id": vid})
        print("REGISTERED %s -> %s ep%d" % (fname, sid, num))
    if changed:
        manifest["videos"] = videos
        save_manifest(manifest)
        summary["changed_paths"] = ["videos.enc"]
        summary["commit_message"] = (
            "Auto-register own videos: " + "; ".join(msgs))
    with open(os.path.join(REPO_ROOT, ".auto-register-summary.json"),
              "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
