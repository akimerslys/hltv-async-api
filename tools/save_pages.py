"""Save HLTV pages as .html.gz so they can be shared (e.g. dropped into tests/data) and parsers built from real HTML.

    python tools/save_pages.py URL [URL ...] [--out tests/data] [--name NAME]

Uses the library's own Selenium driver (pip install "hltv-async-api[selenium]"), so it passes the same Cloudflare check
your browser does. One Chrome window is opened for all URLs. Every page is written to ``<out>/<name>.html.gz`` and
listed in ``<out>/_sources.json`` with its URL and the save time.
"""

import argparse
import gzip
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hltv_async_api.selenium_driver import SeleniumDriver  # noqa: E402


def default_name(url: str) -> str:
    path = urlparse(url).path.strip('/')
    return re.sub(r'[^a-z0-9]+', '_', path.lower()).strip('_') or 'home'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('urls', nargs='+')
    parser.add_argument('--out', default='tests/data')
    parser.add_argument('--name', help='file name for a single URL (default: derived from the URL path)')
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sources_file = out / '_sources.json'
    sources = json.loads(sources_file.read_text(encoding='utf-8')) if sources_file.exists() else {}

    driver = SeleniumDriver()
    try:
        for url in args.urls:
            name = args.name if args.name and len(args.urls) == 1 else default_name(url)
            html = driver.get_html(url)
            if not html:
                print(f'FAILED  {url} (Cloudflare check did not finish)')
                continue
            with gzip.open(out / f'{name}.html.gz', 'wt', encoding='utf-8') as file:
                file.write(html)
            sources[name] = {'url': url, 'saved': datetime.now(timezone.utc).strftime('%Y-%m-%d')}
            print(f'saved   {url} -> {out / (name + ".html.gz")}')
    finally:
        driver.close()
        sources_file.write_text(json.dumps(sources, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
