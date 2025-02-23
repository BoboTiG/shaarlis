"""
Tests:
    python -m doctest sync.py
"""
from contextlib import suppress
import http.client
import json
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

MANUAL = Path("manual.json")
BAD = Path("bad.json")
SHAARLIS = Path("shaarlis.json")
URLS = [
    ("json", "https://www.ecirtam.net/shaarli-api/feeds?full=1"),
    ("json", "https://flow.2038.net/api/feeds?full=1"),
    ("json", "https://links.shikiryu.com/api/feeds?full=1"),
    # ("opml", "https://www.shaarlo.fr/opml.php"),
    ("opml", "https://links.shikiryu.com/api/feeds?format=opml"),
]
UNWANTED_URL_PATH_PARTS = {
    "atom",
    "feed",
    "index.html",
    "index.php",
    "index.php5",
    "rss",
    "rss.xml",
}


def sanitize_url(url: str) -> str:
    """
    # Standard
    >>> sanitize_url("https://example.org/?do=atom")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/?do=rss")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/feed/atom")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/feed/rss")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/feed/rss?do=atom")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/feed/rss?do=rss")
    'https://example.org/?do=rss'

    # Subfolder
    >>> sanitize_url("https://example.org/shaarli/?do=atom")
    'https://example.org/shaarli?do=rss'
    >>> sanitize_url("https://example.org/shaarli/?do=rss")
    'https://example.org/shaarli?do=rss'
    >>> sanitize_url("https://example.org/shaarli/feed/atom")
    'https://example.org/shaarli?do=rss'
    >>> sanitize_url("https://example.org/shaarli/feed/rss")
    'https://example.org/shaarli?do=rss'
    >>> sanitize_url("https://example.org/shaarli/feed/rss?do=atom")
    'https://example.org/shaarli?do=rss'
    >>> sanitize_url("https://example.org/shaarli/feed/rss?do=rss")
    'https://example.org/shaarli?do=rss'

    # BlogoText / oText
    >>> sanitize_url("https://example.org/rss.php?mode=links&do=rss")
    'https://example.org/rss.php?mode=links&do=rss'

    # Weird
    >>> sanitize_url("")
    ''
    >>> sanitize_url("https://example.org//?do=rss")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org//feed?do=rss")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/?do=rss?")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/index.php?do=rss&")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/index.php5?do=rss")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/shaarli/feed/feed/rss")
    'https://example.org/shaarli/feed?do=rss'
    >>> sanitize_url("https://example.org/rss.xml")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/?kw=computer%20services")
    'https://example.org/?do=rss'
    >>> sanitize_url("https://example.org/carnet.atom")
    'https://example.org/carnet.atom?do=rss'
    """
    if not url:
        return ""

    parts = urlparse(url)

    path = list(Path(parts.path).parts)
    for unwanted in UNWANTED_URL_PATH_PARTS:
        while unwanted in path:
            path.remove(unwanted)
    path = "/".join(path).strip("/")

    # BlogoText / oText support
    query = "mode=links&do=rss" if path.endswith("rss.php") else "do=rss"

    parts = parts._replace(path=path or "/", query=query)
    return urlunparse(parts)


def get_dynamic_feeds(kind: str, url: str) -> set[str]:
    try:
        data = urlopen(url).read()
    except http.client.IncompleteRead as exc:
        data = exc.partial

    match kind:
        case "json":
            urls = (feed["url"] for feed in json.loads(data))
        case "opml":
            urls = re.findall(r'xmlUrl="([^"]+)"', data.decode())
    return {sanitize_url(url) for url in urls}


def get_bad_feeds() -> set[str]:
    return {sanitize_url(url) for url in json.loads(BAD.read_text())}


def get_current_feeds() -> set[str]:
    return {sanitize_url(url) for url in json.loads(SHAARLIS.read_text())}


def get_manual_feeds() -> set[str]:
    return {sanitize_url(url) for url in json.loads(MANUAL.read_text())}


def main():
    current_feeds = get_current_feeds()
    new_feeds = get_manual_feeds()
    bad_feeds = get_bad_feeds()

    for kind, url in URLS:
        new_feeds.update(get_dynamic_feeds(kind, url))

    diff = new_feeds - current_feeds - bad_feeds
    new = 0
    for feed_url in diff:
        if (
            feed_url
            and feed_url.replace("http:", "https:") not in current_feeds
            and feed_url.replace("https:", "http:") not in current_feeds
        ):
            print(f'"{feed_url}",')
            new += 1

    print(f"+ {new}")


if __name__ == "__main__":
    main()
