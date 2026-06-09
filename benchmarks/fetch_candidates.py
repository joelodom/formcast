#!/usr/bin/env python3
"""Fetch benchmark candidate photos (single object, plain background) with licenses.

Primary source: Openverse API (CC0/PD filter). Fallback: Wikimedia Commons search
with incategory hints. Downloads into benchmarks/cache/candidates/<class>/ with a
sidecar .json (title/license/source) per image. Gentle pacing to respect servers.

Run from repo root:  python3 benchmarks/fetch_candidates.py [class ...]
"""
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())
UA = {"User-Agent": "formcast-research/0.1 (benchmark photo acquisition for a procedural-3D research project)"}

OPENVERSE = "https://api.openverse.org/v1/images/"
COMMONS = "https://commons.wikimedia.org/w/api.php"

QUERIES = {
    "boulder": {"openverse": ["boulder isolated", "granite boulder", "rock white background"],
                "commons": ['glacial erratic boulder filetype:bitmap']},
    "flower":  {"openverse": ["tulip white background", "flower isolated white background"],
                "commons": ['incategory:"Flowers on white background"']},
    "chair":   {"openverse": ["wooden chair white background", "chair isolated white background"],
                "commons": ['chair incategory:"Chairs" filetype:bitmap white background']},
    "table":   {"openverse": ["wooden table white background", "table isolated furniture"],
                "commons": ['table furniture filetype:bitmap white background']},
}
PER_CLASS = 5
SLEEP = 2.0


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
        return json.loads(r.read().decode())


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60, context=SSL_CTX) as r:
        data = r.read()
    if len(data) < 10_000:
        raise ValueError(f"suspiciously small ({len(data)} bytes)")
    dest.write_bytes(data)


def openverse_search(term, n=8):
    qs = urllib.parse.urlencode({
        "q": term, "license": "cc0,pdm", "page_size": str(n),
        "filter_dead": "true",
    })
    data = get_json(f"{OPENVERSE}?{qs}")
    out = []
    for r in data.get("results", []):
        out.append({"title": r.get("title", ""), "license": r.get("license", ""),
                    "source": r.get("foreign_landing_url") or r.get("url", ""),
                    "url": r.get("url", ""), "provider": r.get("provider", "")})
    return out


def commons_search(term, n=8):
    qs = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": term, "gsrnamespace": "6", "gsrlimit": str(n),
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": "1280",
    })
    data = get_json(f"{COMMONS}?{qs}")
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for p in pages.values():
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "").lower()
        if not any(k in lic for k in ("cc0", "public domain", "pd", "cc by")):
            continue
        out.append({"title": p.get("title", ""), "license": lic,
                    "source": info.get("descriptionurl", ""),
                    "url": info.get("thumburl") or info.get("url", ""),
                    "provider": "wikimedia"})
    return out


def main():
    only = set(sys.argv[1:])
    base = Path(__file__).parent / "cache" / "candidates"
    summary = {}
    for klass, srcs in QUERIES.items():
        if only and klass not in only:
            continue
        outdir = base / klass
        outdir.mkdir(parents=True, exist_ok=True)
        n, seen = 0, set()
        candidates = []
        for term in srcs["openverse"]:
            try:
                candidates += openverse_search(term)
                time.sleep(SLEEP)
            except Exception as e:
                print(f"[{klass}] openverse '{term}': {e}", file=sys.stderr)
        for term in srcs["commons"]:
            try:
                candidates += commons_search(term)
                time.sleep(SLEEP)
            except Exception as e:
                print(f"[{klass}] commons '{term}': {e}", file=sys.stderr)
        for r in candidates:
            if n >= PER_CLASS:
                break
            url = r["url"]
            if not url or url in seen:
                continue
            ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
            if ext not in (".jpg", ".jpeg", ".png"):
                continue
            seen.add(url)
            dest = outdir / f"{n:02d}{ext}"
            try:
                download(url, dest)
            except Exception as e:
                print(f"[{klass}] dl fail {r['title'][:40]}: {e}", file=sys.stderr)
                continue
            dest.with_suffix(".json").write_text(json.dumps(r, indent=1))
            print(f"[{klass}] {dest.name}  {r['license']:<10} {r['provider']:<12} {r['title'][:60]}")
            n += 1
            time.sleep(SLEEP)
        summary[klass] = n
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
