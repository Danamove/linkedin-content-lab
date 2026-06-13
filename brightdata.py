"""Thin Bright Data Web Unlocker REST client.

Returns clean markdown for any public URL, mirroring what the MCP
`scrape_as_markdown` tool returns (BD does the HTML->markdown conversion).

Contract (https://api.brightdata.com/request):
    POST, header Authorization: Bearer <API_KEY>
    body {"zone","url","format":"raw","data_format":"markdown","country":...}
"""
import os
import time
import requests

ENDPOINT = "https://api.brightdata.com/request"


class BrightDataError(RuntimeError):
    pass


def _load_env():
    """Load BRIGHTDATA_* from a sibling .env if not already in the environment."""
    api_key = os.environ.get("BRIGHTDATA_API_KEY")
    zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE")
    if api_key and zone:
        return api_key, zone
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
        api_key = os.environ.get("BRIGHTDATA_API_KEY")
        zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE")
    if not api_key or not zone:
        raise BrightDataError(
            "Missing BRIGHTDATA_API_KEY / BRIGHTDATA_UNLOCKER_ZONE "
            "(set them in the environment or in .env)."
        )
    return api_key, zone


def scrape_markdown(url, country="us", timeout=90, retries=3, backoff=8):
    """Scrape `url` via Web Unlocker and return the page as markdown text.

    Retries on network errors and 5xx with linear backoff.
    """
    api_key, zone = _load_env()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "zone": zone,
        "url": url,
        "format": "raw",
        "data_format": "markdown",
    }
    if country:
        payload["country"] = country

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(ENDPOINT, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(backoff * attempt)
            continue
        if resp.status_code == 200:
            return resp.text
        if resp.status_code in (401, 403):
            raise BrightDataError(f"Auth failed ({resp.status_code}): check API key / zone.")
        if resp.status_code == 400:
            raise BrightDataError(f"Bad request (400): {resp.text[:300]}")
        # 5xx / 429 -> retry
        last_err = BrightDataError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        time.sleep(backoff * attempt)
    raise BrightDataError(f"Failed after {retries} attempts: {last_err}")
