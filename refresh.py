"""LinkedIn Content Lab — weekly refresh pipeline.

Two-pass, mirroring sourcing-lab:
  Pass 1: scrape each influencer's public recent-activity page -> their own post URLs
  Pass 2: scrape each NEW (or still-maturing) post -> reactions / comments / body
Then merge, prune to the rolling window, compute per-author outlier ratios, render.

Run:  python refresh.py            (full run, all influencers)
      python refresh.py glencathey (single handle, for testing)
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

import parse
from brightdata import scrape_markdown, BrightDataError

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
REFRESH_RECENT_DAYS = 14  # re-scrape posts younger than this to let counts mature


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as fh:
        return json.load(fh)


def recent_activity_url(handle):
    return f"https://www.linkedin.com/in/{handle}/recent-activity/all/"


def load_posts(handle):
    path = os.path.join(DATA_DIR, f"{handle}_posts.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return {p["id"]: p for p in json.load(fh).get("posts", [])}
    return {}


def save_posts(handle, name, posts):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{handle}_posts.json")
    payload = {
        "handle": handle,
        "name": name,
        "updated": datetime.now(timezone.utc).isoformat(),
        "posts": sorted(posts, key=lambda p: p["date"], reverse=True),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def age_days(iso_date, now):
    return (now - datetime.fromisoformat(iso_date)).days


def median(values):
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def band_for(ratio, bands):
    if ratio >= bands["breakout"]:
        return "breakout"
    if ratio >= bands["replicable"]:
        return "replicable"
    if ratio >= bands["working"]:
        return "working"
    return "baseline"


def _candidates(md, handle, name):
    """Build the unified work-list of items (posts + articles) from a Pass-1 page."""
    items = []
    for p in parse.extract_own_posts(md, handle):
        items.append({
            "id": p["activity_id"], "url": p["url"], "kind": "post",
            "date": parse.activity_id_to_dt(p["activity_id"]).isoformat(),
        })
    for a in parse.extract_articles(md, name):
        items.append({
            "id": "pulse:" + a["key"], "url": a["url"], "kind": "article",
            "date": a["date"],  # may be None until Pass 2
        })
    return items


def refresh_influencer(inf, cfg, now):
    handle, name = inf["handle"], inf["name"]
    country = cfg.get("country", "us")
    window_days = cfg.get("window_days", 90)
    existing = load_posts(handle)

    # Pass 1 — list own posts + articles
    try:
        md = scrape_markdown(recent_activity_url(handle), country=country)
    except BrightDataError as exc:
        print(f"  ! {handle}: pass-1 failed: {exc}")
        return list(existing.values())
    cands = _candidates(md, handle, name)
    n_post = sum(1 for c in cands if c["kind"] == "post")
    print(f"  {handle}: {n_post} posts + {len(cands) - n_post} articles on activity page")

    merged = dict(existing)
    for c in cands:
        cid, url, kind, listing_date = c["id"], c["url"], c["kind"], c["date"]
        # window pre-filter when we already know the date (free for posts)
        if listing_date and (now - datetime.fromisoformat(listing_date)).days > window_days:
            continue
        need_pass2 = (cid not in existing) or (
            existing[cid].get("date") and age_days(existing[cid]["date"], now) < REFRESH_RECENT_DAYS)
        if not need_pass2:
            continue
        try:
            page = scrape_markdown(url, country=country)
        except BrightDataError as exc:
            print(f"    ! {kind} {cid}: {exc}")
            continue
        parsed = parse.parse_post(page)
        date = listing_date
        if kind == "article":
            pub = parse.parse_published_date(page)
            date = (pub.isoformat() if pub else None) or listing_date \
                or (existing.get(cid, {}).get("date"))
        merged[cid] = {"id": cid, "url": url, "kind": kind, "date": date, **parsed}
        time.sleep(1)  # be polite

    # prune to window (drop items still missing a date)
    in_window = [
        p for p in merged.values()
        if p.get("date") and (now - datetime.fromisoformat(p["date"])).days <= window_days
    ]

    # per-author outlier ratio
    bands = cfg.get("outlier_bands", {"working": 2, "replicable": 5, "breakout": 15})
    min_n = cfg.get("min_posts_for_baseline", 4)
    eng = [p["engagement"] for p in in_window]
    base = median([e for e in eng if e > 0]) or 1
    for p in in_window:
        if len(in_window) < min_n:
            p["ratio"], p["band"] = None, "n/a"
        else:
            p["ratio"] = round(p["engagement"] / base, 2)
            p["band"] = band_for(p["ratio"], bands)
        p["name"] = name

    save_posts(handle, name, in_window)
    return in_window


def main():
    cfg = load_config()
    now = datetime.now(timezone.utc)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    influencers = [i for i in cfg["influencers"] if not only or i["handle"] == only]
    if not influencers:
        print(f"No influencer matched '{only}'")
        return

    all_posts = []
    for inf in influencers:
        all_posts.extend(refresh_influencer(inf, cfg, now))

    # render dashboard from everything on disk (not just this run's subset)
    import build
    build.render(ROOT)
    print(f"Done. {len(all_posts)} posts processed this run.")


if __name__ == "__main__":
    main()
