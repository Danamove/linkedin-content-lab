# LinkedIn Content Lab — Plan

Adapted from `Danamove/sourcing-lab` (Instagram → LinkedIn). Clean new repo.
Goal: **learn content patterns** — surface which posts overperformed *for their own author*,
study the hook (first line) + topic + format. NOT a generic "most likes" board.

## Decisions (locked with Dana)
- **Source:** Bright Data Web Unlocker REST API (token + zone in `.env`). Proven: a single public
  post scrape returns full body text + reactions + comments, no login.
- **Metric:** per-author outlier. `ratio = post_engagement / author_median_engagement`, where
  `engagement = reactions + comments` (+ reposts if available). Bands ≥2 / ≥5 / ≥15.
- **Runtime:** local Windows Task Scheduler, weekly. Windowless launcher (VBS) to avoid console flash.
- **Repo:** new `Danamove/linkedin-content-lab`. Local dev: `OneDrive\Desktop\linkedin-content-lab\`.
- **Dropped from sourcing-lab:** ffmpeg, video clips, transcripts, Apify. None apply to text posts.
- **Reality check acknowledged:** these recruiting/HR influencers get dozens–low-hundreds of
  reactions, not "tens of thousands." Per-author metric makes that irrelevant (relative, not absolute).

## Influencer list (22)
Dana's 6: charlywargnier, glencathey, lizryan, milesjennings, louisetriance, hunglee
From Phil's post (16): amymencarelli, traciesponenberg, adrianoherdman1 (uk), michaelbrown91281,
alexseiler, beneubanks, keriohlrich, larsschmidt, danfromhr, hunglee (dup), haileygeorge,
stacyzapar, cammasfreeman, kieran-snyder, kylelagunas, hannahmorgan
Plus author: philstrazzulla
→ 22 unique (hunglee dedup). Note country subdomains: adrianoherdman1 = uk, hunglee = uk.

## Architecture (Python + static HTML, mirrors sourcing-lab)
```
linkedin-content-lab/
  config.json            # 22 influencers: {handle, name, profile_url, subdomain}
  .env                   # BRIGHTDATA_API_TOKEN, BRIGHTDATA_ZONE  (gitignored)
  .env.example
  brightdata.py          # thin Web Unlocker REST client (token+zone -> markdown)
  refresh.py             # pipeline orchestrator (two-pass)
  build.py               # render index.html from data/*.json
  data/{handle}_posts.json   # committed state per influencer
  index.html             # generated dashboard
  run_refresh.vbs        # windowless launcher for Task Scheduler
  tests/smoke_test.py    # offline parser tests on saved fixtures
```

## Two-pass pipeline (refresh.py)
- **Pass 1 — list (1 scrape/influencer):** scrape `{sub}linkedin.com/in/{handle}/recent-activity/all/`.
  - Own posts = post URLs whose slug **before `_`** equals the handle (locale-proof; do NOT parse the
    "Posted by"/"likes this" label — it localizes with the BD exit node, e.g. Danish "Opslået af").
  - Pulse articles: listing already carries reaction + comment counts → can skip Pass 2 for articles.
  - Dedupe by activity id; only NEW post ids go to Pass 2.
- **Pass 2 — engagement (1 scrape/new post):** scrape each new `/posts/{handle}_..._activity-{id}-xxx`
  → full body text, reactions, comments (regex over markdown, validated against the proven sample).
- Merge into `data/{handle}_posts.json`; prune posts older than rolling window (default 90 days, configurable).
- Compute per-author median + outlier ratio + band. Call build.py.

## Dashboard (build.py → index.html)
- Card/table per post: hook (first line, emphasized), author, date, reactions, comments,
  outlier ratio, band, link to post.
- Client-side sort: outlier ratio (default) / absolute engagement / date / author. Filter by author + band.
- Vanilla JS, no framework, no DB — same as sourcing-lab.

## Scheduling
- `run_refresh.vbs` runs python refresh.py windowless (per the console-flash lesson).
- Weekly Task Scheduler trigger (e.g. Sunday 07:00).
- Optional: git commit + push updated index.html/data to GitHub Pages for anywhere-viewing.

## Risks to validate DURING build (not blockers)
1. **Exact Web Unlocker REST contract** — confirm endpoint/payload (zone, url, format) via BD docs/Sophie
   before writing brightdata.py.
2. **Guest pagination** — recent-activity guest view showed ~5–10 own posts + articles. Enough for a
   "recent winners" window; validate per influencer. If too thin, fall back to BD's structured LinkedIn
   dataset API (returns posts+engagement as JSON) — note as upgrade path, keep markdown-parse first (simplicity).
3. **Count parsing robustness** — reactions/comments live in `trk=public_post_social-actions-*` links;
   parse those, add a fixture test.
4. **Cost** — ~22 list + ~150 post scrapes/week ≈ cents on Web Unlocker. Fine.

## Build steps (checkable)
- [x] 1. Web Unlocker REST contract confirmed from official BD docs (POST /request, format:raw +
      data_format:markdown). Live call pending Dana's creds in .env.
- [x] 2. Scaffolded: config.json (22), .env.example, .gitignore, requirements.txt.
- [x] 3. brightdata.py — REST client with .env loader + retry/backoff.
- [x] 4. Pass 1 — own-post extraction by URL slug. Tested (own vs liked, subdomains).
- [x] 5. Pass 2 — per-post reactions/comments/body/hook. Tested on real Phil(139/65)+Joveo(57/23).
- [x] 6. Merge/dedupe/prune + per-author outlier ratio + bands + activity-id→date trick.
- [x] 7. build.py → index.html dashboard (sort/filter/search, hook-first). Screenshotted.
- [x] 8. tests/smoke_test.py (3 unit) + tests/integration_test.py (offline wiring). All pass.
- [x] 9. run_refresh.vbs windowless launcher. Task Scheduler registration pending Dana's OK on timing.
- [~] 10. Pipeline verified offline on real fixtures end-to-end. Live 22-influencer run pending creds.
- [ ] 11. (optional) GitHub repo Danamove/linkedin-content-lab + Pages push.

## Review
Built a clean LinkedIn port of sourcing-lab. Verified empirically at every layer that could be
verified without Dana's Bright Data credentials:
- **API contract** confirmed from Bright Data's official docs (not guessed).
- **Parser** unit-tested on two REAL scraped posts (Phil 139/65, Joveo 57/23) — counts, hook, and
  own-vs-liked discrimination all correct. Caught + fixed two real bugs: (a) boilerplate filter killed
  body lines containing inline @mention links → strip links first; (b) subdomain regex `[a-z]{2}` missed
  `www.` (3 letters) → allow any subdomain.
- **Full refresh wiring** (Pass1→Pass2→prune→metric→render) integration-tested offline by monkeypatching
  the network with real fixtures. Produces correct JSON + index.html.
- **Dashboard** rendered + screenshotted (preview.png).

**Yield gap caught + fixed (advisor flag).** Measured real own-post yield across authors before
declaring done: hunglee 0, stacyzapar 0, glencathey 2, lizryan 9 — three below the threshold, two
totally empty. But every author surfaces ~9-10 Pulse articles, and an article page returns the SAME
`social-actions-reactions` markup as a post, so one parser handles both. Added article capture to
Pass 1/2 (URL by author name-slug, date from "Published …"/listing). Now every author clears the
baseline. Tested end-to-end (article path in integration_test).

**Live run done.** Bright Data creds located in `.claude.json` (hosted-MCP token works as the REST
Bearer; zone `mcp_unlocker`), written to `.env`. Ran all 22 live → **142 items, 20 authors, 0 artifacts**.
Top outliers: Charly Wargnier 69.6× (link-share), Alex Seiler 19.2×, Adriano Herdman 7.7× (Claude-prompts
giveaway). 1-2 authors (haileygeorge) intermittently hit a guest login-wall; a re-run fills them.

**Parser hardened on live data** (9 tests now): the "longest line = body" heuristic needed 5 chrome
filters found only by scanning all live hooks — consent line, image link, cookie banner, page-title meta,
orphaned link fragment. See lessons.md.

What's left (optional): scheduled-task registration, GitHub repo. The pipeline is live and clean.
