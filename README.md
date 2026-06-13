# LinkedIn Content Lab

Track public LinkedIn posts from a hand-picked list of influencers and surface
**which posts overperform for their own author** — so you can study the content
patterns (hook, topic, format) that actually earn engagement.

Adapted from [`sourcing-lab`](https://github.com/Danamove/sourcing-lab) (Instagram → LinkedIn).
Same shape: a Python pipeline + a static HTML dashboard, no database, no server.

![preview](preview.png)

## How it works
- **Source:** Bright Data Web Unlocker (scrapes public pages, no login).
- **Pass 1** — scrape each influencer's public `recent-activity` page → their own **posts**
  (own vs. liked decided by URL slug, locale-proof) **and Pulse articles** (`/pulse/` links,
  filtered to the author's name-slug). Articles matter: many authors surface mostly articles to
  logged-out visitors, so posts-only would leave them blank.
- **Pass 2** — scrape each new/maturing post or article → reactions, comments, body, hook.
  Post and article pages share the same `social-actions` markup, so one parser handles both.
- **Metric** — per-author outlier ratio = `post engagement ÷ that author's median`.
  Bands: Working ≥2×, Replicable ≥5×, Breakout ≥15×. (Absolute "most likes" would just
  resurface the biggest account every week; per-author is what teaches patterns.)
- **Dashboard** — `index.html`, sortable/filterable, hook emphasized.

## Setup
1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env` and fill in your Bright Data Web Unlocker credentials:
   ```
   BRIGHTDATA_API_KEY=...
   BRIGHTDATA_UNLOCKER_ZONE=...
   ```
   (Control Panel → your Web Unlocker zone → Overview tab.)
3. Edit `config.json` to set the influencer list and tuning (`window_days`, bands, etc.).

## Run
```
python refresh.py            # full run, all influencers -> data/*.json + index.html
python refresh.py glencathey # single handle, for testing
python build.py              # re-render index.html from existing data only
```
Open `index.html` in a browser.

## Schedule (weekly, Windows)
Task Scheduler → Create Task → Action:
```
Program:   wscript.exe
Arguments: "C:\Users\USER\OneDrive\Desktop\linkedin-content-lab\run_refresh.vbs"
```
The VBS launcher runs `refresh_and_publish.bat` hidden (no console-window flash): it refreshes the
data, then `git commit` + `git push` so the live GitHub Pages dashboard auto-updates. Writes `refresh.log`.

**Live dashboard:** https://danamove.github.io/linkedin-content-lab/

## Tests
```
python tests/smoke_test.py        # parser unit tests on real saved fixtures
python tests/integration_test.py  # full refresh wiring, offline (monkeypatched fetch)
```

## Notes
- Recruiting/HR influencers run dozens–low-hundreds of reactions, not tens of thousands —
  the per-author metric is what makes small and large accounts comparable.
- Real yield measured on the guest page (own posts / Pulse articles): hung lee 0/10, stacy zapar
  0/9, glen cathey 2/~10, liz ryan 9/10. That's why articles are captured, not just posts — and why
  the metric needs `min_posts_for_baseline` (default 4) to avoid noisy ratios on thin authors.
- `country` is pinned to `us` so dates/labels come back in English (the date parser expects
  `Mon D, YYYY`). If you change it, re-check date parsing.
- For deeper history than the guest page exposes, Bright Data's structured LinkedIn dataset API
  (JSON posts+engagement) is the upgrade path — swap it into `refresh.py` Pass 1/2.
