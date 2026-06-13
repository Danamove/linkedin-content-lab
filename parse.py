"""Pure parsing helpers — no network. Unit-tested against saved fixtures.

Two jobs:
  1. extract_own_posts(md, handle)  -> own post URLs + ids from a recent-activity page
  2. parse_post(md)                 -> reactions / comments / body / hook from a single post page
"""
import re
from datetime import datetime, timezone

# Full canonical post URL: /posts/{handle}_{slug}-activity-{id}-{code}
_POST_URL = re.compile(
    r"https?://(?:[a-z0-9-]+\.)*linkedin\.com/posts/"
    r"([a-z0-9\-]+?)_[^\s)\"'\\]*?activity-(\d+)-[A-Za-z0-9_\-]+",
    re.IGNORECASE,
)

# Pulse article URL: /pulse/{title-slug}-{author-name-slug}-{code}
_PULSE_URL = re.compile(
    r"https?://(?:[a-z0-9-]+\.)*linkedin\.com/pulse/[A-Za-z0-9][A-Za-z0-9\-]*",
    re.IGNORECASE,
)
# English date as pinned by country=us, e.g. "Jun 9, 2026" / "Published Jun 9, 2026"
_DATE = re.compile(r"([A-Z][a-z]{2})\s+(\d{1,2}),\s+(\d{4})")
_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

# Main-post engagement (first occurrence = the post itself, not feed neighbours)
_REACTIONS = re.compile(r"\[([\d,]+)\]\([^)]*?social-actions-reactions")
_COMMENTS = re.compile(r"\[([\d,]+)\s*Comments?\]\([^)]*?social-actions-comments")

# Boilerplate markers that disqualify a line from being the post body.
# Checked case-insensitively AFTER stripping markdown links, so URL-only tokens
# (trk=, etc.) are gone — these match the visible boilerplate TEXT only.
_BOILER = (
    "agree & join", "skip to main content", "summarized by ai",
    "welcome back", "report this", "join now",
    # consent / login-wall lines (these were leaking through as fake hooks)
    "you agree to linkedin", "by clicking continue", "join or sign in",
    "sign in to view", "sign in to see", "create your free account",
    "to view or add a comment", "new to linkedin", "better on the app",
    "get the app", "don't have the app",
    "non-essential cookies", "3rd parties use", "to show you relev",
)
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")  # [*] allows empty-text image links []( )
# Page <title> / heading meta: "{excerpt} | {Author} | N comments" or "… | LinkedIn"
_TITLE_META = re.compile(r"\|\s*\d+\s+comments?\s*$|\|\s*LinkedIn\s*$", re.IGNORECASE)


def activity_id_to_dt(activity_id):
    """LinkedIn activity/share ids embed the creation time in their high bits
    (ms since the Unix epoch, shifted left 22). Returns a UTC datetime."""
    ms = int(activity_id) >> 22
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


def _clean_num(s):
    return int(s.replace(",", ""))


def extract_own_posts(markdown, handle):
    """Return [{activity_id, url}] for posts authored by `handle`.

    Own vs liked/reshared is decided by the URL slug (the part before `_`),
    which is locale-proof — unlike the on-page "Posted by" label that changes
    with the Bright Data exit-node language.
    """
    seen = {}
    for m in _POST_URL.finditer(markdown):
        slug_handle, activity_id = m.group(1).lower(), m.group(2)
        if slug_handle != handle.lower():
            continue
        if activity_id not in seen:
            seen[activity_id] = m.group(0)
    return [{"activity_id": aid, "url": url} for aid, url in seen.items()]


def _parse_date(text):
    m = _DATE.search(text or "")
    if not m or m.group(1) not in _MONTHS:
        return None
    return datetime(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)),
                    tzinfo=timezone.utc)


def parse_published_date(markdown):
    """Date from a Pulse article page ('Published Jun 9, 2026'). UTC datetime or None."""
    m = re.search(r"Published\s+" + _DATE.pattern, markdown)
    return _parse_date(m.group(0)) if m else None


def _name_slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def extract_articles(markdown, name=None):
    """Return [{url, key, date}] for Pulse articles on an author's page.

    Pulse URLs embed the author-name slug (…-glen-cathey-4qm0e); when `name` is
    given we keep only matching URLs (drops any recommended article from others).
    `date` is parsed from the listing text near each link (may be None)."""
    slug = _name_slug(name) if name else None
    seen = {}
    for m in _PULSE_URL.finditer(markdown):
        url = m.group(0).split("?")[0]
        key = url.rsplit("/pulse/", 1)[-1].lower()
        if slug and slug not in key:
            continue
        if key in seen:
            continue
        dt = _parse_date(markdown[m.end():m.end() + 400])
        seen[key] = {"url": url, "key": key, "date": dt.isoformat() if dt else None}
    return list(seen.values())


def _strip_links(text):
    return _MD_LINK.sub(r"\1", text).replace("\\", "").strip()


def _strip_leading_title(text):
    """Drop the leading ```…``` fenced block — it's the page <title>
    ('{excerpt} | {Author} | N comments'), which otherwise wins on short posts."""
    m = re.match(r"\s*```.*?```", text, re.S)
    return text[m.end():] if m else text


def _extract_body(markdown, reactions_idx):
    """Body = the longest substantial line (after stripping inline links) above
    the engagement counts. Anchoring on the first counts keeps us inside the
    main post, before any feed neighbours."""
    head = _strip_leading_title(markdown[:reactions_idx])
    candidates = []
    for ln in head.splitlines():
        stripped = _strip_links(ln.strip())
        if len(stripped) < 40:
            continue
        if stripped.startswith("]"):  # orphaned link fragment ']( https://… )'
            continue
        low = stripped.lower()
        if any(b in low for b in _BOILER):
            continue
        if _TITLE_META.search(stripped):  # page-title / heading meta line
            continue
        candidates.append(stripped)
    if not candidates:
        return ""
    return max(candidates, key=len)


def _hook(body, limit=140):
    if not body:
        return ""
    first = re.split(r"(?<=[.!?])\s|\n", body, maxsplit=1)[0].strip()
    if len(first) > limit:
        first = first[:limit].rstrip() + "…"
    return first


def parse_post(markdown):
    """Parse a single public post page -> dict with engagement + text."""
    r = _REACTIONS.search(markdown)
    c = _COMMENTS.search(markdown)
    reactions = _clean_num(r.group(1)) if r else 0
    comments = _clean_num(c.group(1)) if c else 0
    # anchor body extraction on whichever count link appears first
    idxs = [m.start() for m in (r, c) if m]
    anchor = min(idxs) if idxs else len(markdown)
    body = _extract_body(markdown, anchor)
    return {
        "reactions": reactions,
        "comments": comments,
        "engagement": reactions + comments,
        "text": body,
        "hook": _hook(body),
    }
