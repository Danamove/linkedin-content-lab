# Lessons — LinkedIn Content Lab

## Parsing LinkedIn public-post markdown

`[ERROR]` Body-extraction filtered out any line containing `trk=` as "boilerplate".
The real post body contains inline `@mention` links whose URLs carry `trk=public_post-text`,
so the genuine body line got discarded and the hook came out as a UI artifact
("This title was summarized by AI…").
`[FIX]` Strip markdown links to plain text FIRST, then test for boilerplate on the visible text.
URL-only tokens (`trk=`, `session_redirect`) vanish after stripping, so they no longer false-match.
`[RULE]` When classifying text lines, normalize away link/markup syntax before applying
keyword filters — filter the rendered text a human sees, not the raw markup.

## Subdomain regex

`[ERROR]` Post-URL regex used `(?:[a-z]{2}\.)?linkedin\.com` to allow country subdomains
(`uk.`, `in.`). It silently failed on every `www.linkedin.com` URL because `www` is 3 letters,
not 2 — so own-post extraction returned nothing.
`[FIX]` `(?:[a-z0-9-]+\.)*linkedin\.com` — match any (or no) subdomain.
`[RULE]` Never hard-code a subdomain length. The most common host (`www.`) breaks a `{2}` assumption.
Always test the regex against the real, most-common URL form, not just the edge case you designed for.

## Verifying without credentials

`[RULE]` When the live data source needs the user's secret (BD token), still verify everything else
empirically: confirm the API contract from official docs, unit-test the parser on real saved responses,
and integration-test the full wiring by monkeypatching the network with those fixtures. Only the literal
network round-trip is left to the user — everything else is proven.

## Validate YIELD, not just correctness

`[ERROR]` Tests proved the parser + wiring were correct, but I almost declared done without checking
the one thing that decides if the product works: how many items the source actually returns per entity.
Real own-post yield on LinkedIn guest pages was 0, 0, 2, 9 across four authors — half would render empty
under `min_posts_for_baseline`. A correct pipeline over too-little data is still a dead product.
`[FIX]` Measured yield on ~4 real authors via the MCP (no creds needed), found Pulse articles fill the
gap (every author had ~10), and that article pages share the post `social-actions` markup → one parser.
`[RULE]` For any scrape/collect pipeline, empirically measure items-per-entity against the minimum the
product needs, on a real sample, BEFORE declaring done. "The parser is correct" ≠ "the board is populated."

## Body extraction = whack-a-mole against page chrome (validate on the FULL live set)

`[ERROR]` "Longest non-boilerplate line = post body" passed all fixtures but, on the full 22-author live
run, produced wrong hooks on short posts where a chrome line out-ranked the real body. Found FIVE distinct
chrome patterns only by scanning all 137 live hooks, not the 2 fixtures: (1) consent line "…join or sign
in, you agree to LinkedIn…" (my boilerplate check was case-SENSITIVE and missed lowercase "sign in"); (2)
empty-text image link `[](url)` (strip regex required ≥1 char inside `[]`); (3) cookie banner; (4) page
`<title>`/heading "{excerpt} | {Author} | N comments" (fenced AND repeated plain); (5) orphaned link
fragment `](https://…` from multi-line escaped CTA links.
`[FIX]` Case-insensitive boilerplate; `[^\]]*` (allow empty link text); strip leading ```fence```;
`_TITLE_META` regex for `| N comments`/`| LinkedIn`; skip lines starting with `]`. A short real post with
no text body correctly yields an empty hook ("link-share, no text") — that's honest, not a bug.
`[RULE]` Heuristic text extraction MUST be validated against the full live corpus, not a couple of clean
fixtures. Each chrome pattern is invisible until a short item lets it win. Scan ALL outputs for artifacts
(startswith `[`/`]`, contains `http`, title-meta) and add a regression test per pattern as you find it.
Also: a too-aggressive guard ("drop any line containing http") broke real bodies that share a link —
target the artifact shape precisely, don't blanket-filter.
