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
  3. if the series is already in videos.json -> comment + close, done
  4. harvest the streams via APIShort (anonymous, no key) and merge the
     series into videos.json; the workflow step commits + pushes, then
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
- Sansekai: bandwidth-blocked — never harvest from it. If an issue
  carries source=sansekai, try the same provider via APIShort instead;
  if APIShort has no such provider, comment + close as failed.

Manifest rules: indent=1, raw UTF-8, no trailing newline. Never touch
any other series. Never put any API key in any file or commit.
"""
import json
import os
import re
import sys
import urllib.request
import urllib.error

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"}
API = "https://apishort.com/v1"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPOSITORY", "adam2211dmdm-ux/cinereels-videos")
RESULT = "publish-result.txt"


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
    """APIShort wraps lists under various keys; return the list itself."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("data", "chapters", "episodes", "result", "items", "list"):
            v = data.get(k)
            if isinstance(v, list):
                return v
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
    detail, _ = http_json("%s/reelshort/detail/%s" % (API, book_id))
    d = detail if isinstance(detail, dict) else {}
    book = d.get("data", d) if isinstance(d.get("data", d), dict) else d
    cover = pick(book, "cover", "coverUrl", "poster", "image")
    title = pick(book, "title", "bookName", "name")
    desc = pick(book, "desc", "description", "synopsis")
    chs, _ = http_json("%s/reelshort/chapters/%s" % (API, book_id))
    chapters = as_list(chs)
    if not chapters:
        raise HarvestError("ReelShort: no chapters for book %s" % book_id)
    eps = []
    for i, ch in enumerate(chapters):
        cid = pick(ch, "chapter_id", "chapterId", "id", "chapter_id_str")
        if not cid:
            continue
        play, _ = http_json(
            "%s/reelshort/play/%s?chapter_id=%s" % (API, book_id, cid))
        urls = []
        p = play.get("data", play) if isinstance(play, dict) else {}
        vl = p.get("videoList") or p.get("video_list") or []
        if isinstance(vl, list):
            for u in vl:
                if isinstance(u, dict):
                    urls.append(pick(u, "videoUrl", "url", "playUrl"))
                elif isinstance(u, str):
                    urls.append(u)
        url = ""
        for u in urls:
            if u and "-ld" in u:
                url = u
                break
        if not url:
            url = urls[1] if len(urls) > 1 else (urls[0] if urls else "")
        if not url:
            continue
        eps.append({
            "n": len(eps) + 1,
            "url": url,
            "chapter_id": str(cid),
            "duration": int(pick(ch, "duration", "durationSec", default=90) or 90),
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
    cover = pick(book, "cover", "coverUrl", "poster", "image")
    title = pick(book, "bookName", "title", "name")
    desc = pick(book, "desc", "description", "synopsis")
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
    # Try one search for a cover, best-effort.
    cover = ""
    try:
        res, _ = http_json("%s/netshort/api/search?query=%s"
                           % (API, urllib.request.quote(book_id)))
        for row in as_list(res):
            if str(pick(row, "shortPlayId", "id", default="")) == str(book_id):
                cover = pick(row, "cover", "coverUrl", "poster", "image")
                break
    except Exception:
        cover = ""
    n = int(want_eps or 0)
    if n <= 0:
        raise HarvestError("NetShort: episode count unknown for %s" % book_id)
    eps = [{"n": i + 1, "url": "", "chapter_id": str(i + 1), "duration": 90}
           for i in range(n)]
    return {"cover": cover, "title": "", "desc": "", "episodes": eps}


HARVESTERS = {
    "reelshort": harvest_reelshort,
    "dramabox": harvest_dramabox,
    "shortmax": harvest_shortmax,
    "netshort": harvest_netshort,
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
    if source == "sansekai" and provider in HARVESTERS:
        source = "apishort"  # Sansekai is bandwidth-blocked; same provider via APIShort
    if provider not in HARVESTERS:
        return fail("provider '%s' is not supported for auto-publish." % provider)

    with open("videos.json", encoding="utf-8") as fh:
        manifest = json.load(fh)
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
            "thumbnail_url": cover,
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
    with open("videos.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
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
