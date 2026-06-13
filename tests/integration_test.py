"""Offline integration test of the refresh wiring.

Monkeypatches the Bright Data call with saved real fixtures, runs the full
refresh_influencer() + build.render() chain against a temp data dir, and checks
the produced JSON + index.html. No network, no credentials.

Run: python tests/integration_test.py
"""
import os
import sys
import json
import shutil
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
FX = os.path.join(ROOT, "tests", "fixtures")

import refresh  # noqa: E402
import build  # noqa: E402


def _read(name):
    with open(os.path.join(FX, name), encoding="utf-8") as fh:
        return fh.read()


ARTICLE_PAGE = (
    "Bounded vs Boundless\nPublished Jun 1, 2026\n"
    "This is the full article body text long enough to be picked as the post body line.\n"
    "[15](x?trk=foo_social-actions-reactions) [11 Comments](x?trk=foo_social-actions-comments)\n"
)


def fake_scrape(url, country="us", **kw):
    if "recent-activity" in url:
        return _read("glencathey_activity.txt")
    if "/pulse/" in url:
        return ARTICLE_PAGE
    if "7471180623559331843" in url:
        return _read("phil_post.txt")   # stand-in real post page
    if "7470848493218246656" in url:
        return _read("joveo_post.txt")  # stand-in real post page
    return ""


def main():
    tmp = tempfile.mkdtemp(prefix="lcl_")
    try:
        refresh.scrape_markdown = fake_scrape           # patch network
        refresh.DATA_DIR = os.path.join(tmp, "data")
        cfg = refresh.load_config()
        cfg["min_posts_for_baseline"] = 2               # so a ratio is computed with 2 posts
        now = datetime.now(timezone.utc)

        posts = refresh.refresh_influencer(
            {"handle": "glencathey", "name": "Glen Cathey"}, cfg, now)

        assert len(posts) == 3, f"expected 2 posts + 1 article, got {len(posts)}"
        by_id = {p["id"]: p for p in posts}
        assert by_id["7471180623559331843"]["reactions"] == 139   # phil fixture (post)
        assert by_id["7470848493218246656"]["reactions"] == 57    # joveo fixture (post)
        art = by_id["pulse:bounded-vs-boundless-glen-cathey-abc12"]   # article path
        assert art["kind"] == "article" and art["reactions"] == 15 and art["comments"] == 11
        assert art["date"] == "2026-06-01T00:00:00+00:00"           # from "Published Jun 1, 2026"
        for p in posts:
            assert p["engagement"] == p["reactions"] + p["comments"]
            assert p["ratio"] is not None and p["band"] in (
                "baseline", "working", "replicable", "breakout")
            assert p["hook"]
        print("  ok  refresh_influencer: 2 posts + 1 article, counts + date + ratio + band correct")

        # render dashboard — DATA_DIR already lives under tmp
        build_root = tmp
        build.render(build_root)
        idx = os.path.join(build_root, "index.html")
        assert os.path.exists(idx)
        size = os.path.getsize(idx)
        html_txt = open(idx, encoding="utf-8").read()
        assert "Glen Cathey" in html_txt and "LinkedIn Content Lab" in html_txt
        assert "139" in html_txt and "57" in html_txt
        print(f"  ok  build.render: index.html written ({size} bytes), contains real data")
        print("PASS — integration wiring works end to end")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
