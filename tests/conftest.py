import gzip
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

DATA = Path(__file__).parent / 'data'


@pytest.fixture(scope='session')
def page():
    """Parsed real HLTV page saved in tests/data (see tests/data/_sources.json for URL and snapshot date)."""
    cache = {}

    def load(name: str) -> BeautifulSoup:
        if name not in cache:
            html = gzip.open(DATA / f'{name}.html.gz', 'rt', encoding='utf-8').read()
            cache[name] = BeautifulSoup(html, 'lxml')
        return cache[name]

    return load
