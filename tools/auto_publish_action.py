#!/usr/bin/env python3
"""CineReels auto-publish — GitHub Actions half (runs inside the repo).

Adam imports a series in the app's Admin; the app cannot push to GitHub
itself (no token in the APK — anyone with the APK could extract it and
rewrite the catalog). So the app's "Publish for everyone" button opens a
pre-filled GitHub issue, and this script (every 30 min) turns the oldest
open "[CineReels Publish]" issue into a public series:

  1. list open issues titled "[CineReels Publish] ..." (oldest first)
  2. parse the body (series_id / title_en / title_ar / provider /
     book_id / source / episodes)
  3. if the series is already in videos.enc -> comment + close, done
  4. harvest the streams via APIShort (anonymous, no key) and merge the
     series into videos.enc; the workflow step commits + pushes, then
     closes the issue
  5. permanent failures (book not found, unknown provider) -> comment
     the reason + close, so they never retry forever
  6. quota-out -> exit 2 with NO comment and NO close; the next run
     retries once the daily budget resets

Per-provider rules (verified 2026-11-24):
- ReelShort: detail + chapters + play per chapter_id; bake urls[1]
  (540p H264 -ld.m3u8). NEVER urls[0] (720p H265 = black screen).
- DramaBox: detail + allepisode (one call, all episodes); bake
  videoUrl540 for every episode.
- ShortMax / NetShort: stream URLs are tokenized (~8h expiry) — bake
  EMPTY video_url + provider + provider_chapter_id so the app resolves
  the stream live at play time. ShortMax is best-effort (its segments
  may carry custom encryption a stock player cannot play).
- GoodShort (v1.40): book + chapters; chapters are SIGNED HLS m3u8 —
  bake EMPTY video_url + chapter numbers, live-resolve at play.
  Cover from book.cover.
- Anichin (v1.40): NO separate harvester — an issue with
  source=anichin is harvested via APIShort by provider (same provider
  names overlap) and published with provider_source=apishort.
- Sansekai: bandwidth-blocked — never harvest from it. If an issue
  carries source=sansekai, try the same provider via APIShort instead;
  if APIShort has no such provider, comment + close as failed.

Manifest rules: the catalog on disk is videos.enc — base64 single-line
AES-256-CBC of the JSON (indent=1, raw UTF-8, no trailing newline).
Decrypt with MANIFEST_KEY / MANIFEST_IV (repo secrets) at start, work
on the plaintext in memory, re-encrypt on write. NEVER write a
plaintext videos.json. Never touch any other series. Never put any API
key in any file or commit.
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
import urllib.parse

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"}
API = "https://apishort.com/v1"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "adam2211dmdm-ux/cinereels-videos")
RESULT = "publish-result.txt"
MANIFEST_ENC = "videos.enc"


# ---------------------------------------------------------------- manifest crypto
# v1.48: the catalog on disk is videos.enc (base64 single-line AES-256-CBC).
# Key/IV come from the MANIFEST_KEY / MANIFEST_IV env vars (repo secrets
# set from the same key file the app build uses). openssl is used for the
# cipher — no extra pip dependency on the runner.

def manifest_crypto():
    """(key_hex, iv_hex) from env. Raises HarvestError when missing."""
    key = os.environ.get("MANIFEST_KEY", "")
    iv = os.environ.get("MANIFEST_IV", "")
    if len(key) != 64 or len(iv) != 32:
        raise HarvestError("MANIFEST_KEY/IV missing or wrong length "
                           "(need 64/32 hex chars)")
    return key, iv


def load_manifest():
    """Decrypt videos.enc -> parsed manifest dict."""
    key, iv = manifest_crypto()
    try:
        with open(MANIFEST_ENC, encoding="utf-8") as fh:
            raw = base64.b64decode(fh.read().strip())
    except Exception as e:
        raise HarvestError("cannot read %s: %s" % (MANIFEST_ENC, e))
    r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc",
                        "-K", key, "-iv", iv],
                       input=raw, capture_output=True)
    if r.returncode != 0:
        raise HarvestError("manifest decrypt failed (openssl exit %d)"
                           % r.returncode)
    try:
        return json.loads(r.stdout.decode("utf-8"))
    except Exception as e:
        raise HarvestError("decrypted manifest is not JSON: %s" % e)


def save_manifest(manifest):
    """Serialize (indent=1, no trailing newline) -> encrypt -> videos.enc."""
    key, iv = manifest_crypto()
    text = json.dumps(manifest, ensure_ascii=False, indent=1)
    r = subprocess.run(["openssl", "enc", "-aes-256-cbc",
                        "-K", key, "-iv", iv],
                       input=text.encode("utf-8"), capture_output=True)
    if r.returncode != 0:
        raise HarvestError("manifest encrypt failed (openssl exit %d)"
                           % r.returncode)
    with open(MANIFEST_ENC, "w", encoding="utf-8") as fh:
        fh.write(base64.b64encode(r.stdout).decode("ascii") + "\n")


class QuotaOut(Exception):
    pass


class HarvestError(Exception):
    pass


def http_json(url, timeout=30):
    """GET url -> (parsed json, X-RateLimit-Remaining or None)."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            remaining = r.headers.get("X-RateLimit-Remaining")
            raw = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            raise QuotaOut("APIShort HTTP %s on %s" % (e.code, url))
        raise HarvestError("APIShort HTTP %s on %s" % (e.code, url))
    except Exception as e:
        raise HarvestError("fetch failed %s: %s" % (url, e))
    try:
        data = json.loads(raw, strict=False)
    except Exception:
        raise HarvestError("bad JSON from %s" % url)
    rem = None
    if remaining is not None:
        try:
            rem = int(remaining)
        except ValueError:
            rem = None
    if rem is not None and rem < 5:
        raise QuotaOut("APIShort quota nearly out (remaining=%s)" % rem)
    return data, rem


def as_list(data):
    """APIShort wraps lists under various keys; return the list itself.
    Recurses into dict wrappers (e.g. ShortMax alleps is
    {"data": {"episodes": [...]}} — "data" is a dict, not a list)."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("data", "chapters", "episodes", "result", "items", "list"):
            v = data.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                r = as_list(v)
                if r:
                    return r
    return []


def pick(d, *keys, default=""):
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return default


# ---------------------------------------------------------------- GitHub

def gh(method, path, body=None):
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Authorization": "Bearer " + TOKEN,
               "Accept": "application/vnd.github+json", **UA}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", "replace")
    return json.loads(raw) if raw.strip() else {}


def list_publish_issues():
    issues = gh("GET", "/repos/%s/issues?state=open&per_page=50"
                "&sort=created&direction=asc" % REPO)
    out = []
    for it in issues:
        if "pull_request" in it:
            continue
        if it.get("title", "").startswith("[CineReels Publish]"):
            out.append(it)
    return out


def comment_and_close(number, comment):
    gh("POST", "/repos/%s/issues/%d/comments" % (REPO, number),
       {"body": comment})
    gh("PATCH", "/repos/%s/issues/%d" % (REPO, number), {"state": "closed"})


def parse_body(body):
    fields = {}
    for line in (body or "").splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line.strip())
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


# ---------------------------------------------------------------- harvest

def harvest_reelshort(book_id, want_eps):
    # v1.38 fix (verified live 2026-11-25): the /play endpoint IGNORES
    # chapter_id — it returns episode 1's streams for every chapter, so
    # the old per-chapter play loop baked episode 1's URL 51 times.
    # /allepisodes returns every episode's own streams in ONE call;
    # the -ld (540p H264) file is derived from each episode's own
    # h264-narrow-sd.m3u8 (same base path, -ld instead of -sd).
    detail, _ = http_json("%s/reelshort/detail/%s" % (API, book_id))
    d = detail if isinstance(detail, dict) else {}
    book = d.get("data", d) if isinstance(d.get("data", d), dict) else d
    # v1.38: the detail object carries the poster as "pic" (not
    # "cover") — the old keys returned empty, so a published ReelShort
    # series got a blank cover.
    cover = pick(book, "pic", "cover", "coverUrl", "poster", "image")
    title = pick(book, "title", "bookName", "name")
    desc = pick(book, "desc", "description", "synopsis")
    all_eps, _ = http_json("%s/reelshort/allepisodes/%s" % (API, book_id))
    rows = as_list(all_eps)
    if not rows:
        raise HarvestError("ReelShort: no episodes for book %s" % book_id)
    eps = []
    for row in rows:
        url = ""
        for s in (row.get("streams") or []):
            u = s.get("url", "") if isinstance(s, dict) else ""
            if not u:
                continue
            if "-ld.m3u8" in u:
                url = u
                break
            if not url and "h264-narrow-sd.m3u8" in u:
                url = u.replace("h264-narrow-sd.m3u8", "h264-narrow-ld.m3u8")
        if not url:
            continue
        eps.append({
            "n": len(eps) + 1,
            "url": url,
            "chapter_id": str(pick(row, "id", "chapter_id", "chapterId", default="")),
            "duration": int(pick(row, "duration", "durationSec", default=90) or 90),
        })
    if not eps:
        raise HarvestError("ReelShort: no playable episodes for %s" % book_id)
    return {"cover": cover, "title": title, "desc": desc, "episodes": eps}


def harvest_dramabox(book_id, lang):
    detail, _ = http_json(
        "%s/dramabox/api/dramabox/detail?bookId=%s&lang=%s"
        % (API, book_id, lang))
    d = detail if isinstance(detail, dict) else {}
    book = d.get("data", d) if isinstance(d.get("data", d), dict) else d
    # v1.38: the live detail object is FLAT with coverWap (not
    # "cover") and "introduction" (not "desc") — the old keys returned
    # empty, so a published DramaBox series got a blank cover.
    cover = pick(book, "coverWap", "cover", "coverUrl", "poster", "image")
    title = pick(book, "bookName", "title", "name")
    desc = pick(book, "desc", "description", "introduction", "synopsis")
    alleps, _ = http_json(
        "%s/dramabox/api/dramabox/allepisode?bookId=%s" % (API, book_id))
    rows = as_list(alleps)
    if not rows:
        raise HarvestError("DramaBox: no episodes for book %s" % book_id)
    eps = []
    for row in rows:
        url = pick(row, "videoUrl540", "videoUrl", "videoUrl720")
        if not url:
            continue
        eps.append({
            "n": len(eps) + 1,
            "url": url,
            "chapter_id": str(pick(row, "chapterId", "chapter_id", "id", default="")),
            "duration": int(pick(row, "duration", "durationSec", default=90) or 90),
        })
    if not eps:
        raise HarvestError("DramaBox: no playable episodes for %s" % book_id)
    return {"cover": cover, "title": title, "desc": desc, "episodes": eps}


def harvest_shortmax(book_id, want_eps):
    alleps, _ = http_json(
        "%s/shortmax/api/v1/alleps/%s?lang=id" % (API, book_id))
    rows = as_list(alleps)
    if not rows:
        raise HarvestError("ShortMax: no episodes for %s" % book_id)
    eps = []
    for row in rows:
        eps.append({
            "n": len(eps) + 1,
            "url": "",  # tokenized (~8h) — resolved live at play
            "chapter_id": str(pick(row, "code", "chapterId", "id", default="")),
            "duration": 90,
        })
    return {"cover": "", "title": "", "desc": "", "episodes": eps}


def harvest_netshort(book_id, want_eps):
    # No stable URLs to bake; the app resolves each episode live.
    # Cover comes from the drama detail endpoint: the old best-effort
    # search by numeric book id returned nothing, so published NetShort
    # series always got a blank cover (blank posters in the app).
    # Percent-encode the URL: it carries non-ASCII characters and the
    # app fetches cover_url with a raw URL.
    cover = ""
    try:
        res, _ = http_json("%s/netshort/api/drama/%s?lang=en" % (API, book_id))
        data = res.get("data", {}) if isinstance(res, dict) else {}
        raw = pick(data, "shortPlayCover", "cover", "coverUrl", "poster", "image")
        if raw:
            parts = urllib.parse.urlsplit(raw)
            cover = urllib.parse.urlunsplit((parts.scheme, parts.netloc,
                                             urllib.parse.quote(parts.path),
                                             parts.query, parts.fragment))
    except Exception:
        cover = ""
    n = int(want_eps or 0)
    if n <= 0:
        raise HarvestError("NetShort: episode count unknown for %s" % book_id)
    eps = [{"n": i + 1, "url": "", "chapter_id": str(i + 1), "duration": 90}
           for i in range(n)]
    return {"cover": cover, "title": "", "desc": "", "episodes": eps}


def harvest_goodshort(book_id, want_eps):
    # v1.40: GoodShort via APIShort. Detail = /book/{id}?lang=en (NOT
    # /detail — 404); episodes = /chapters/{id}?lang=en (NOT
    # /allepisodes — 404). Chapters return SIGNED HLS m3u8 with an
    # expiry token — bake EMPTY video_url + chapter numbers so the app
    # resolves the stream live at play time (same class as ShortMax /
    # NetShort). Cover comes from book.cover (acfs1.goodreels.com).
    book, _ = http_json("%s/goodshort/book/%s?lang=en" % (API, book_id))
    b = book.get("data", {}).get("book", {}) if isinstance(book, dict) else {}
    cover = pick(b, "cover", "bookDetailCover", "coverUrl", "poster", "image")
    title = pick(b, "bookName", "title", "name")
    desc = pick(b, "introduction", "desc", "description", "synopsis")
    chapters, _ = http_json("%s/goodshort/chapters/%s?lang=en" % (API, book_id))
    rows = as_list(chapters)
    if not rows:
        raise HarvestError("GoodShort: no episodes for book %s" % book_id)
    eps = []
    for row in rows:
        idx = row.get("index")
        n = (int(idx) + 1) if idx is not None else len(eps) + 1
        try:
            dur = int(row.get("playTime") or 90)
        except (TypeError, ValueError):
            dur = 90
        eps.append({
            "n": n,
            "url": "",  # signed HLS — resolved live at play
            "chapter_id": str(n),
            "duration": dur,
        })
    eps.sort(key=lambda e: e["n"])
    return {"cover": cover, "title": title, "desc": desc, "episodes": eps}


HARVESTERS = {
    "reelshort": harvest_reelshort,
    "dramabox": harvest_dramabox,
    "shortmax": harvest_shortmax,
    "netshort": harvest_netshort,
    "goodshort": harvest_goodshort,
}


# ---------------------------------------------------------------- main

def main():
    if not TOKEN:
        print("GITHUB_TOKEN missing", file=sys.stderr)
        return 2
    issues = list_publish_issues()
    if not issues:
        print("no publish issues")
        return 0
    issue = issues[0]
    number = issue["number"]
    f = parse_body(issue.get("body", ""))
    sid = f.get("series_id", "")
    provider = (f.get("provider", "") or "").lower()
    book_id = f.get("book_id", "")
    source = (f.get("source", "") or "").lower()
    want_eps = int(f.get("episodes", "0") or 0)
    title_en = f.get("title_en", "")
    title_ar = f.get("title_ar", "")

    def fail(msg):
        comment_and_close(number, "❌ Publish failed: %s" % msg)
        with open(RESULT, "w", encoding="utf-8") as fh:
            fh.write("changed=false\nstatus=failed\n")
        print("failed: %s" % msg)
        return 0

    if not sid or not provider or not book_id:
        return fail("the issue is missing series_id / provider / book_id.")
    # v1.40: Anichin issues harvest via APIShort by provider (the
    # provider names overlap) — no separate Anichin harvester here;
    # the published series resolves through APIShort in the app.
    if source in ("sansekai", "anichin") and provider in HARVESTERS:
        source = "apishort"  # Sansekai is bandwidth-blocked; same provider via APIShort
    if provider not in HARVESTERS:
        return fail("provider '%s' is not supported for auto-publish." % provider)

    try:
        manifest = load_manifest()
    except HarvestError as e:
        print("manifest unavailable: %s" % e, file=sys.stderr)
        return 2
    if any(s.get("id") == sid for s in manifest.get("series", [])):
        comment_and_close(number, "✅ Already public — '%s' is already in the catalog." % (title_en or sid))
        with open(RESULT, "w", encoding="utf-8") as fh:
            fh.write("changed=false\nstatus=already-public\n")
        print("already public: %s" % sid)
        return 0

    try:
        if provider == "dramabox":
            res = harvest_dramabox(book_id, "ar" if title_ar else "en")
        elif provider == "reelshort":
            res = harvest_reelshort(book_id, want_eps)
        elif provider == "shortmax":
            res = harvest_shortmax(book_id, want_eps)
        elif provider == "goodshort":
            res = harvest_goodshort(book_id, want_eps)
        else:
            res = harvest_netshort(book_id, want_eps)
    except QuotaOut as e:
        print("quota out, leaving issue open: %s" % e, file=sys.stderr)
        return 2
    except HarvestError as e:
        return fail(str(e))

    eps = res["episodes"]
    lang = "ar" if (provider == "dramabox" and title_ar) else "en"
    cover = res["cover"] or ""
    # Episode thumbnails are origin-checked by the app
    # (ManifestLoader.isSameOriginManifest): a foreign-host thumbnail
    # rejects the WHOLE remote manifest. Series cover_url is NOT
    # checked, so a foreign cover is fine there — episode rows fall
    # back to the series cover in the app (HomeActivity).
    ALLOWED_THUMB_HOSTS = ("raw.githubusercontent.com", "narto-drama.com",
        "img.nartodrama-api.online", "v-mps.crazymaplestudios.com",
        "v-img.crazymaplestudios.com", "hwztakavideoto.dramaboxdb.com",
        "hwztchapter.dramaboxdb.com")
    thumb = cover if cover and urllib.parse.urlsplit(cover).netloc in ALLOWED_THUMB_HOSTS else ""
    series = {
        "category_id": "drama",
        "cover_url": cover,
        "description": res["desc"] or title_en,
        "description_ar": title_ar,
        "episode_ids": ["%s-ep%d" % (sid, e["n"]) for e in eps],
        "free_episodes": 25,
        "id": sid,
        "provider": provider,
        "provider_book_id": book_id,
        "provider_source": "apishort",
        "title": res["title"] or title_en,
        "title_ar": title_ar,
    }
    videos = []
    for e in eps:
        n = e["n"]
        videos.append({
            "id": "%s-ep%d" % (sid, n),
            "series_id": sid,
            "episode_number": n,
            "title_en": "Episode %d" % n,
            "title_ar": "الحلقة %d" % n,
            "description_en": "",
            "description_ar": "",
            "category": "drama",
            "duration_sec": e["duration"],
            "video_url": e["url"],
            "thumbnail_url": thumb,
            "language": lang,
            "subtitle_default": "ar",
            "likes_count": 0,
            "views_count": 0,
            "is_published": True,
            "tags": ["drama"],
            "is_locked": n > 25,
            "status": "published",
            "coming_soon": False,
            "views": 0,
            "burned_subs": False,
            "web_page": False,
            "provider": provider,
            "provider_chapter_id": e["chapter_id"] or None,
        })
    manifest.setdefault("series", []).append(series)
    manifest.setdefault("videos", []).extend(videos)
    try:
        save_manifest(manifest)
    except HarvestError as e:
        print("manifest save failed: %s" % e, file=sys.stderr)
        return 2
    with open(RESULT, "w", encoding="utf-8") as fh:
        fh.write("changed=true\n")
        fh.write("issue=%d\n" % number)
        fh.write("title=%s\n" % (res["title"] or title_en))
        fh.write("episodes=%d\n" % len(eps))
        fh.write("provider=%s\n" % provider)
    print("baked %s: %d episodes" % (sid, len(eps)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
