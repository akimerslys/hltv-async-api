"""Parsers and URL builders for HLTV's player statistics pages (``/stats/players/...``).

Every page can be filtered (map, event type, dates, opponent ranking, ...), see :func:`player_query`.
"""

import json
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

import pytz

from hltv_async_api.Utils.numbers import to_float, to_int

BASE_URL = 'https://www.hltv.org'

MAP_CODES = {'anc': 'Ancient', 'mrg': 'Mirage', 'nuke': 'Nuke', 'inf': 'Inferno', 'd2': 'Dust2', 'ovp': 'Overpass',
             'vtg': 'Vertigo', 'anb': 'Anubis', 'cch': 'Cache', 'trn': 'Train', 'cbl': 'Cobblestone', 'tcn': 'Tuscan',
             'season': 'Season', 'mrd': 'Mirage'}
_MATCH_TYPES = {'majors': 'Majors', 'bigevents': 'BigEvents', 'mvpevents': 'MvpEvents', 'lan': 'Lan', 'online': 'Online'}
_PLAYOFF = {'grandfinal': 'GRAND_FINAL', 'playoffs': 'PLAYOFFS', 'preplayoff': 'PRE_PLAYOFF'}


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', (text or '').lower().replace('+', ' plus ')).strip('_')


def _norm(text) -> str:
    return re.sub(r'[^a-z0-9]', '', str(text).lower())


def player_query(cs_version: str | None = 'CS2', map: str | None = None, match_type: str | None = None,
                 start_date: str | None = None, end_date: str | None = None, ranking: int | None = None,
                 best_of: int | None = None, ranked: bool | None = None, playoff: str | None = None,
                 team_id: int | None = None, opponent_team: int | None = None, event: int | None = None,
                 offset: int | None = None, fast: bool = False) -> str:
    """Query string of the filters HLTV understands. ``None`` leaves a filter off.

    :param cs_version: ``'CS2'`` (default), ``'CSGO'`` or ``None`` for both.
    :param map: ``'mirage'``, ``'de_mirage'``, ...
    :param match_type: ``'majors'``, ``'big_events'``, ``'mvp_events'``, ``'lan'`` or ``'online'``.
    :param start_date: / ``end_date``: ``'YYYY-MM-DD'``; ``start_date='all'`` removes any date limit.
    :param ranking: only matches against the top ``5 / 10 / 20 / 30 / 50`` teams.
    :param best_of: ``1``, ``3`` or ``5``.
    :param ranked: ``True`` for Valve ranked events, ``False`` for unranked.
    :param playoff: ``'grand_final'``, ``'playoffs'`` or ``'pre_playoff'``.
    :param team_id: only matches played for this team. ``opponent_team``: only matches against this team.
    :param offset: skip this many rows (tables show 100 per page). ``fast``: fast multi-kills only.
    """
    query: dict[str, str | int] = {}
    if offset:
        query['offset'] = int(offset)
    if fast:
        query['fast'] = 'true'
    if cs_version:
        query['csVersion'] = cs_version.upper()
    if map:
        name = str(map).lower()
        query['maps'] = name if name.startswith('de_') else f'de_{name}'
    if match_type:
        key = _norm(match_type)
        if key not in _MATCH_TYPES:
            raise ValueError(f'match_type must be one of {sorted(_MATCH_TYPES.values())}')
        query['matchType'] = _MATCH_TYPES[key]
    if start_date:
        query['startDate'] = start_date
    if end_date:
        query['endDate'] = end_date
    if ranking:
        query['rankingFilter'] = f'Top{int(ranking)}'
    if best_of:
        query['bestOfX'] = f'BestOf{int(best_of)}'
    if ranked is not None:
        query['valveRanked'] = 'RANKED' if ranked else 'UNRANKED'
    if playoff:
        key = _norm(playoff)
        if key not in _PLAYOFF:
            raise ValueError(f'playoff must be one of {sorted(_PLAYOFF.values())}')
        query['playoffMatchType'] = _PLAYOFF[key]
    if team_id:
        query['teamId'] = int(team_id)
    if opponent_team:
        query['opponentTeam'] = int(opponent_team)
    if event:
        query['event'] = int(event)
    return urlencode(query)


def player_url(page: str, player_id, nickname: str, variant: str | None = None, **filters) -> str:
    """URL of a statistics page. ``page``: overview, advanced, matches, events, career, weapon, clutches, multikills, opponents."""
    nick = re.sub(r'[^a-z0-9]+', '-', str(nickname).lower()).strip('-') or 'player'
    player_id = int(player_id)
    if page == 'overview':
        path = f'/stats/players/{player_id}/{nick}'
    elif page in ('clutches', 'multikills'):
        path = f'/stats/players/{page}/{player_id}/{variant or ("all" if page == "clutches" else "two")}/{nick}'
    elif page == 'opponents':
        path = f'/stats/players/opponents/{variant or "team"}/{player_id}/{nick}'
    else:
        path = f'/stats/players/{page}/{player_id}/{nick}'
    query = player_query(**filters)
    return f'{BASE_URL}{path}' + (f'?{query}' if query else '')


def _clean_number(text: str) -> str:
    return (text or '').replace('−', '-').replace('–', '-').replace('\xa0', ' ')


def number(text: str):
    """'+0.65%' -> 0.65, '$2,293' -> 2293, '0m 51s' -> 51 (seconds), '-' -> None, '12' -> 12."""
    text = _clean_number(text).strip()
    if not text or text in ('-', '--', 'N/A'):
        return None
    time = re.fullmatch(r'(?:(\d+)m)?\s*(?:(\d+)s)?', text)
    if time and (time.group(1) or time.group(2)):
        return int(time.group(1) or 0) * 60 + int(time.group(2) or 0)
    match = re.search(r'[+-]?\d[\d,]*(?:\.\d+)?', text)
    if not match:
        return None
    raw = match.group().replace(',', '')
    return float(raw) if '.' in raw else int(raw)


def anchor_nick(row) -> str:
    anchor = row.select_one('a[href*="/stats/players/"]')
    return anchor.get_text(strip=True) if anchor else ''


def clutch_variant(size) -> str:
    """'all', 3, '1on3' -> 'all' / '1on3'."""
    text = str(size).lower().replace(' ', '')
    if text == 'all':
        return 'all'
    digit = re.search(r'[1-5]$', text)
    if not digit:
        raise ValueError("clutch size must be 'all' or 1-5 (1on1 ... 1on5)")
    return f'1on{digit.group()}'


def multikill_variant(kills) -> str:
    """'all', 3, 'three', '3x' -> 'all' / 'two' / 'three' / 'four' / 'five'."""
    text = str(kills).lower().strip()
    names = {'2': 'two', '3': 'three', '4': 'four', '5': 'five'}
    text = names.get(text.rstrip('x'), text)
    if text not in ('all', 'two', 'three', 'four', 'five'):
        raise ValueError("kills must be 'all' or 2-5 (two ... five)")
    return text


class PlayerStats:
    def __init__(self, tz):
        self.TIMEZONE = tz

    # -------------------------------------------------------------- helpers

    @staticmethod
    def _id(href, kind) -> int:
        match = re.search(rf'/{kind}/(?:\w+/)?(\d+)', href or '')
        return int(match.group(1)) if match else 0

    def _date(self, cell) -> dict:
        div = cell.select_one('[data-unix]') if cell else None
        if div is None:
            return {'timestamp': 0, 'date': ''}
        timestamp = to_int(div.get('data-unix')) // 1000
        moment = datetime.fromtimestamp(timestamp, timezone.utc)
        if self.TIMEZONE:
            moment = moment.astimezone(pytz.timezone(self.TIMEZONE))
        return {'timestamp': timestamp, 'date': moment.strftime('%d-%m-%Y')}

    @staticmethod
    def _team(cell) -> dict:
        """{'id', 'name', 'score'} from a table cell holding a team link and an optional '(13)'."""
        scope = cell.select_one('.gtSmartphone-only') or cell
        link = scope.select_one('a[href*="/stats/teams/"]')
        score = re.search(r'\((\d+)\)', scope.get_text(' '))
        if link is None:
            return {'id': 0, 'name': scope.get_text(strip=True), 'score': to_int(score.group(1)) if score else 0}
        return {'id': PlayerStats._id(link.get('href'), 'teams'), 'name': link.get_text(strip=True),
                'score': to_int(score.group(1)) if score else 0}

    @staticmethod
    def _map(cell) -> dict:
        if cell is None:
            return {'map_code': '', 'map': ''}
        short, full = cell.select_one('.dynamic-map-name-short'), cell.select_one('.dynamic-map-name-full')
        code = (short or cell).get_text(strip=True)
        return {'map_code': code, 'map': full.get_text(strip=True) if full else MAP_CODES.get(code, code)}

    @staticmethod
    def _rows(page):
        table = page.select_one('table.stats-table')
        return table.select('tbody tr') if table else []

    @staticmethod
    def _cells(row) -> list:
        return [td for td in row.find_all('td', recursive=False) if 'smartphone-only' not in (td.get('class') or [])]

    @staticmethod
    def _pagination(page) -> dict:
        data = page.select_one('.pagination-data')
        numbers = [int(n) for n in re.findall(r'\d+', data.get_text() if data else '')]
        if len(numbers) < 3:
            return {'from': 0, 'to': 0, 'total': 0}
        return {'from': numbers[0], 'to': numbers[1], 'total': numbers[2]}

    @staticmethod
    def _summary_boxes(page) -> dict:
        boxes = {}
        for box in page.select('.summary .summary-box'):
            value, desc = box.select_one('.value'), box.select_one('.description')
            if value is None or desc is None:
                continue
            label = ''.join(desc.find_all(string=True, recursive=False)).strip()
            boxes[slug(label)] = number(value.get_text())
        return boxes

    @staticmethod
    def _chart(node) -> dict | None:
        try:
            return json.loads(node['data-chartjs-config'])
        except (KeyError, TypeError, ValueError):
            return None

    # -------------------------------------------------------------- overview

    @staticmethod
    def _roles(page) -> dict:
        roles = {}
        for section in page.select('.role-stats-section'):
            name = next((c[5:] for c in section.get('class', []) if c.startswith('role-') and c != 'role-stats-section'), '')
            if not name:
                continue
            scores = {}
            for wrapper in section.select('.role-stats-section-title-wrapper'):
                side = next((c[11:] for c in wrapper.get('class', []) if c.startswith('stats-side-')), 'combined')
                value = wrapper.select_one('.role-stats-section-score-value')
                scores[side] = to_int(value.get_text()) if value else 0
            stats = {}
            for row in section.select('.role-stats-row'):
                side = next((c[11:] for c in row.get('class', []) if c.startswith('stats-side-')), 'combined')
                title = row.select_one('.role-stats-title .gtSmartphone-only') or row.select_one('.role-stats-title')
                data = row.select_one('.role-stats-data')
                if not title or not data:
                    continue
                bar = row.select_one('.role-stats-progress')
                band = next((c for c in (bar.get('class') or []) if c != 'role-stats-progress'), '') if bar else ''
                entry = stats.setdefault(slug(title.get_text()), {'title': title.get_text(strip=True)})
                entry['value' if side == 'combined' else side] = number(data.get_text())
                if side == 'combined':
                    entry['band'] = band
            roles[name] = {'score': scores.get('combined', 0), 'ct_score': scores.get('ct', 0),
                           't_score': scores.get('t', 0), 'stats': stats}
        return roles

    @staticmethod
    def _headline(page, title):
        node = page.find(string=re.compile(rf'^\s*{title}\s*$'))
        return node.parent.parent if node is not None else None

    def get_player_overview(self, r) -> dict:
        left = r.select_one('.player-summary-stat-box-left')
        link = left.select_one('a.player-summary-stat-box-left-team-logo-wrapper') if left else None
        logo = link.find('img') if link else None
        profile = left.select_one('a.player-summary-stat-box-left-btn') if left else None
        flag = left.select_one('.player-summary-stat-box-left-flag img') if left else None
        nickname = left.select_one('.player-summary-stat-box-left-nickname') if left else None
        real_name = left.select_one('.player-summary-stat-box-left-player-name') if left else None
        age = left.select_one('.player-summary-stat-box-left-player-age') if left else None
        text = r.get_text(' ')
        maps = re.search(r'(\d+)\s+maps', text)

        summary, verdicts = {}, {}
        for wrapper in r.select('.player-summary-stat-box-data-wrapper'):
            label = wrapper.select_one('.player-summary-stat-box-data-text')
            value = wrapper.select_one('.player-summary-stat-box-data')
            if not label or not value:
                continue
            key = slug(''.join(label.find_all(string=True, recursive=False)))
            summary[key] = number(value.get_text())
            verdict = wrapper.select_one('.player-summary-stat-box-breakdown-description')
            if verdict:
                verdicts[key] = verdict.get_text(strip=True)
        rating = r.select_one('.player-summary-stat-box-rating-data-text')
        if rating:
            summary['rating'] = number(rating.get_text())
            verdict = r.select_one('.player-summary-stat-box-rating-text')
            verdicts['rating'] = verdict.get_text(strip=True) if verdict else ''
        for side in ('t', 'ct'):
            box = r.select_one(f'.player-summary-stat-box-side-rating.{side}-rating')
            if box:
                summary[f'{side}_rating'] = number(''.join(box.find(string=True, recursive=True) or '0'))

        unique_similar = []
        for row in r.select('.similar-player-row'):
            anchor = row.select_one('a[href*="/stats/players/"]')
            row_flag = row.select_one('img.flag')
            skip = re.compile(r'^(\d+\s*%|Similar|Go to .*|Add to .*|Create .*)$')
            tokens = [t for t in row.get_text('|', strip=True).split('|')
                      if t and not skip.match(t) and t != anchor_nick(row)]
            percent = re.search(r'(\d+)\s*%', row.get_text(' '))
            if anchor is None:
                continue
            unique_similar.append({
                'id': self._id(anchor.get('href'), 'players'), 'nickname': anchor.get_text(strip=True),
                'country': row_flag.get('title', '') if row_flag else '',
                'team': tokens[0] if tokens else '',
                'similarity': to_int(percent.group(1)) if percent else 0})

        featured = []
        for box in r.select('.rating-breakdown'):
            description = box.select_one('.rating-description')
            top = re.search(r'top\s*(\d+)', description.get_text() if description else '')
            featured.append({'label': description.get_text(strip=True) if description else '',
                             'top': to_int(top.group(1)) if top else 0,
                             'rating': to_float((box.select_one('.rating-value') or box).get_text()),
                             'maps': to_int((box.select_one('.rating-maps') or box).get_text())})

        teammates = []
        for box in r.select('.teammate'):
            anchor = box.select_one('a.image-and-label')
            country = box.select_one('img.flag')
            teammates.append({'id': self._id(anchor.get('href') if anchor else '', 'players'),
                              'nickname': anchor.get_text(strip=True) if anchor else '',
                              'country': country.get('title', '') if country else '',
                              'rating': to_float((box.select('.teammate-info > span') or [box])[-1].get_text())})

        return {
            'id': self._id(profile.get('href') if profile else '', 'player'),
            'nickname': nickname.get_text(strip=True) if nickname else '',
            'name': real_name.get_text(strip=True) if real_name else '',
            'age': to_int(age.get_text()) if age else 0,
            'country': flag.get('title', '') if flag else '',
            'team': {'id': self._id(link.get('href') if link else '', 'teams'), 'name': logo.get('title', '') if logo else ''},
            'maps': to_int(maps.group(1)) if maps else 0,
            'summary': summary,
            'verdicts': verdicts,
            'roles': self._roles(r),
            'similar_players': unique_similar,
            'featured_ratings': featured,
            'teammates': teammates,
        }

    # -------------------------------------------------------------- advanced

    def get_player_advanced(self, r) -> dict:
        text = r.get_text(' ')
        maps = re.search(r'(\d+)\s+maps\s*\W+\s*(\d+)\s+rounds', text)

        def tile(node) -> dict:
            label = node.select_one('.advanced-tile-label > span')
            value = node.select_one('.advanced-tile-value')
            detail = node.select_one('.advanced-tile-detail')
            bar = node.select_one('.advanced-bar-fill')
            detail_text = detail.get_text(' ', strip=True) if detail else ''
            return {'label': label.get_text(strip=True) if label else '',
                    'value': number(value.get_text()) if value else None,
                    'text': value.get_text(strip=True) if value else '',
                    'detail': {k.lower(): number(v) for k, v in re.findall(r'([A-Za-z]+)\s+(\S+)', _clean_number(detail_text))},
                    'band': next((c for c in (bar.get('class') or []) if c != 'advanced-bar-fill'), '') if bar else ''}

        sections = {}
        for section in r.select('.advanced-section'):
            title = section.select_one('.standard-headline')
            key = slug(title.get_text()) if title else f'section_{len(sections) + 1}'
            entry: dict = {'title': title.get_text(strip=True) if title else '',
                           'tiles': [tile(t) for t in section.select('.advanced-tile')]}
            for name, node in ((n, s) for s in section.select('[data-chartjs-config]') for n in ('chart',)):
                config = self._chart(node)
                if not config:
                    continue
                labels = (config.get('data') or {}).get('labels') or []
                datasets = {d.get('label', f'series_{i}'): d.get('data') for i, d in
                            enumerate((config.get('data') or {}).get('datasets') or [])}
                entry[name] = {'labels': labels, 'datasets': datasets}
            sections[key] = entry

        headline = {}
        for node in r.select('.advanced-headline-main .advanced-tile'):
            parsed = tile(node)
            headline[slug(parsed['label'])] = parsed
        return {'maps': to_int(maps.group(1)) if maps else 0, 'rounds': to_int(maps.group(2)) if maps else 0,
                'headline': headline, 'sections': sections}

    # -------------------------------------------------------------- tables

    def get_player_matches(self, r) -> dict:
        rows = []
        for row in self._rows(r):
            cells = row.find_all('td', recursive=False)
            if len(cells) < 6:
                continue
            link = cells[0].select_one('a[href*="mapstatsid"]')
            team, opponent = self._team(cells[1]), self._team(cells[2])
            kills, deaths = (re.findall(r'\d+', cells[4].get_text()) + ['0', '0'])[:2]
            rating = row.select_one('td[class*="rating" i], td.match-won, td.match-lost') or cells[-1]
            rows.append({'stats_id': self._id(link.get('href') if link else '', 'mapstatsid'),
                         **self._date(cells[0]), 'team': team, 'opponent': opponent,
                         **self._map(cells[3]), 'kills': int(kills), 'deaths': int(deaths),
                         'kd_diff': int(kills) - int(deaths), 'rating': to_float(rating.get_text()),
                         'won': team['score'] > opponent['score']})
        return {'summary': self._summary_boxes(r), 'pagination': self._pagination(r), 'matches': rows}

    def get_player_events(self, r) -> dict:
        rows = []
        for row in self._rows(r):
            cells = self._cells(row)  # placement, event, team, maps, KPR - DPR, +/-, rating
            if len(cells) < 7:
                continue
            link = cells[1].select_one('a[href*="event="]')
            team = cells[2].select_one('a[href*="/stats/teams/"]')
            kpr, dpr = (re.findall(r'\d+\.\d+|\d+', cells[4].get_text()) + ['0', '0'])[:2]
            placement = cells[0].get_text(strip=True)
            rows.append({'event_id': to_int(re.search(r'event=(\d+)', link.get('href', '')).group(1)) if link else 0,
                         'event': link.get_text(strip=True) if link else cells[1].get_text(strip=True),
                         'placement': placement, 'place': to_int(placement, 0),
                         'team_id': self._id(team.get('href') if team else '', 'teams'),
                         'team': team.get_text(strip=True) if team else '',
                         'maps': to_int(cells[3].get_text()), 'kpr': float(kpr), 'dpr': float(dpr),
                         'kd_diff': to_int(number(cells[5].get_text()) or 0), 'rating': to_float(cells[6].get_text())})
        return {'pagination': self._pagination(r), 'events': rows}

    def get_player_career(self, r) -> dict:
        def cell(td):
            rating = td.select_one('.stat-rating')
            value = number(rating.get_text()) if rating else None
            if value is None:
                return None
            maps = re.search(r'\((\d+)\)', td.get_text())
            return {'rating': float(value), 'maps': to_int(maps.group(1)) if maps else 0}

        rows = []
        for table in r.select('table.stats-table'):
            for tr in table.select('tbody tr'):
                tds = tr.find_all('td', recursive=False)
                if len(tds) < 5:
                    continue
                rows.append({'period': tds[0].get_text(strip=True), 'all': cell(tds[1]), 'online': cell(tds[2]),
                             'lan': cell(tds[3]), 'majors': cell(tds[4])})
        return {'periods': rows}

    def _history(self, r, kind, size=0) -> dict:
        """Rows of the clutch / multi-kill tables, read by column title (a single-size clutch page has no Type column)."""
        table = r.select_one('table.stats-table')
        headers = ([th.get_text(strip=True).lower() for th in table.select('thead th')
                    if 'smartphone-only' not in (th.get('class') or [])] if table else [])
        rows = []
        for row in self._rows(r):
            cells = self._cells(row)
            if len(cells) < 4 or len(cells) != len(headers):
                continue
            by_name = dict(zip(headers, cells))
            link = cells[0].select_one('a[href*="mapstatsid"]')
            entry = {'stats_id': self._id(link.get('href') if link else '', 'mapstatsid'), **self._date(cells[0]),
                     'team1': self._team(by_name.get('team 1', cells[1])), 'team2': self._team(by_name.get('team 2', cells[2])),
                     **self._map(by_name.get('map', cells[3]))}
            if kind == 'clutches':
                status = by_name['status'].get_text(strip=True) if 'status' in by_name else ''
                kind_cell = by_name.get('type')
                found = re.search(r'1\s*on\s*(\d)', kind_cell.get_text()) if kind_cell else None
                entry.update({'won': status.lower() == 'won', 'clutch': to_int(found.group(1)) if found else size})
            entry['round'] = to_int(by_name['round'].get_text()) if 'round' in by_name else to_int(cells[-1].get_text())
            rows.append(entry)
        return {'pagination': self._pagination(r), 'rows': rows}

    def get_player_clutches(self, r, size: int = 0) -> dict:
        """``size`` is used for pages that only list one clutch size (no Type column)."""
        data = self._history(r, 'clutches', size)
        return {'summary': self._summary_boxes(r), 'pagination': data['pagination'], 'clutches': data['rows']}

    def get_player_multikills(self, r) -> dict:
        data = self._history(r, 'multikills')
        summary = {re.sub(r'^\d+x_', '', key): value for key, value in self._summary_boxes(r).items()}
        return {'summary': summary, 'pagination': data['pagination'], 'multikills': data['rows']}

    def get_player_opponents(self, r) -> dict:
        rows = []
        for row in self._rows(r):
            link = row.select_one('td.teamCol a[href*="/stats/teams/"]')
            cells = row.select('td.statsDetail, td.kdDiffCol, td.ratingCol')
            if link is None or len(cells) < 4:
                continue
            rows.append({'team_id': self._id(link.get('href'), 'teams'),
                         'team': (link.find('img') or link).get('title', link.get_text(strip=True)) if link.find('img') else link.get_text(strip=True),
                         'maps': to_int(cells[0].get_text()), 'kd_diff': to_int(number(cells[1].get_text()) or 0),
                         'kd': to_float(cells[2].get_text()), 'rating': to_float(cells[3].get_text())})
        return {'pagination': self._pagination(r), 'opponents': rows}

    # -------------------------------------------------------------- weapons

    def get_player_weapons(self, r) -> dict:
        def tiles(box):
            return [{'type': t.select_one('.weapon-type-label').get_text(strip=True),
                     'count': to_int(t.select_one('.weapon-type-count').get_text()),
                     'share': to_float(t.select_one('.weapon-type-share').get_text())}
                    for t in box.select('.weapon-type-tile')]

        boxes = r.select('.weapon-overview')
        weapons = []
        for row in r.select('.col.stats-rows .stats-row'):
            name, kills = row.select_one('div'), row.find('span', recursive=False)
            rank = row.select_one('.strong')
            if name and kills:
                label = ''.join(s.get_text() for s in name.find_all('span') if 'strong' not in (s.get('class') or [])).strip()
                weapons.append({'rank': to_int(rank.get_text()) if rank else len(weapons) + 1, 'weapon': label,
                                'kills': to_int(kills.get_text())})
        total = sum(t['count'] for t in tiles(boxes[0])) if boxes else 0
        for weapon in weapons:
            weapon['share'] = round(weapon['kills'] / total * 100, 1) if total else 0.0
        return {'kills_by_type': tiles(boxes[0]) if boxes else [], 'carried_by_type': tiles(boxes[1]) if len(boxes) > 1 else [],
                'weapons': weapons}
