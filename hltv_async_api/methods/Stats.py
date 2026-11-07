"""Parser for HLTV's detailed match statistics (``/stats/matches/<id>/...`` and ``/stats/matches/mapstatsid/<id>/...``).

One page layout serves both the "all maps" overview and a single map, so one parser handles both. The overview page
is covered by a saved real page; the sections that only exist on single-map pages (round history) follow HLTV's
markup from memory and are tolerant: a missing section simply comes back empty.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any

import pytz

from hltv_async_api.Utils.numbers import to_float, to_int

BASE_URL = 'https://www.hltv.org'
_NUMBER = re.compile(r'-?\d+(?:\.\d+)?')


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', (text or '').lower()).strip('_')


def url_slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-') or 'team'


def _num(text: str):
    value = float(text)
    return int(value) if '.' not in text else value


class Stats:
    def __init__(self, tz):
        self.TIMEZONE = tz

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _id(href: str | None, kind: str) -> int:
        match = re.search(rf'/{kind}/(\d+)', href or '')
        return int(match.group(1)) if match else 0

    @staticmethod
    def _two(text: str) -> list[int]:
        return [int(n) for n in re.findall(r'\d+', text or '')]

    def _when(self, info) -> dict:
        span = info.select_one('.small-text span[data-unix]') if info else None
        if span is None:
            return {'timestamp': 0, 'date': '', 'time': ''}
        timestamp = to_int(span.get('data-unix')) // 1000
        moment = datetime.fromtimestamp(timestamp, timezone.utc)
        if self.TIMEZONE:
            moment = moment.astimezone(pytz.timezone(self.TIMEZONE))
        return {'timestamp': timestamp, 'date': moment.strftime('%d-%m-%Y'), 'time': moment.strftime('%H:%M')}

    @staticmethod
    def _map_name(info) -> str:
        small = info.select_one('.small-text') if info else None
        if small is None:
            return ''
        for sibling in small.next_siblings:
            if getattr(sibling, 'name', None):
                break
            text = str(sibling).strip()
            if text:
                return text
        return ''

    @staticmethod
    def _team_box(box) -> dict:
        if box is None:
            return {'id': 0, 'name': '', 'score': 0}
        link = box.select_one('a[href*="/stats/teams/"]')
        logo = box.find('img')
        score = box.select_one('.bold')
        return {'id': Stats._id(link.get('href') if link else '', 'teams'),
                'name': link.get_text(strip=True) if link else (logo.get('title', '') if logo else ''),
                'score': to_int(score.get_text()) if score else 0}

    @staticmethod
    def _breakdown(value) -> dict:
        """'13 : 7 ( 7 : 5 ) ( 6 : 2 )' -> final score plus every half with the side team1 played in it."""
        text = value.get_text(' ', strip=True)
        groups = re.findall(r'\(\s*(\d+)\s*:\s*(\d+)\s*\)', text)
        head = re.match(r'\s*(\d+)\s*:\s*(\d+)', text)
        sides = [('ct' if 'ct-color' in (span.get('class') or []) else 't')
                 for span in value.find_all('span') if {'ct-color', 't-color'} & set(span.get('class') or [])][::2]
        halves = [{'team1': int(a), 'team2': int(b), 'team1_side': sides[i] if i < len(sides) else ''}
                  for i, (a, b) in enumerate(groups)]
        return {'team1': int(head.group(1)) if head else 0, 'team2': int(head.group(2)) if head else 0, 'halves': halves}

    @staticmethod
    def _summary(root) -> dict:
        rows = {}
        for row in root.select('.match-info-row') if root else []:
            label, value = row.select_one('.bold'), row.select_one('.right')
            if not label or not value:
                continue
            if slug(label.get_text()) == 'breakdown' and value.select('.ct-color, .t-color'):
                rows['breakdown'] = Stats._breakdown(value)
                continue
            raw = value.get_text(' ', strip=True)
            numbers = _NUMBER.findall(raw)
            if len(numbers) == 2:
                rows[slug(label.get_text())] = {'team1': _num(numbers[0]), 'team2': _num(numbers[1])}
            else:
                rows[slug(label.get_text())] = {'raw': raw, 'values': [_num(n) for n in numbers]}
        return rows

    @staticmethod
    def _top_players(r) -> dict:
        top = {}
        for box in r.select('.most-x-box'):
            title = box.select_one('.most-x-title')
            link = box.select_one('a[href*="/stats/players/"]')
            value = box.select_one('.valueName')
            if not (title and link and value):
                continue
            top[slug(title.get_text())] = {
                'title': title.get_text(strip=True),
                'player_id': Stats._id(link.get('href'), 'players'),
                'nickname': link.get_text(strip=True),
                'value': to_float(value.get_text()) if '.' in value.get_text() else to_int(value.get_text()),
            }
        return top

    @staticmethod
    def _performance(r) -> list[dict]:
        chart = r.select_one('[data-chartjs-config]')
        if chart is None:
            return []
        try:
            config = json.loads(chart['data-chartjs-config'])
            points = config['data']['datasets'][0]['data']
        except (ValueError, KeyError, IndexError, TypeError):
            return []
        return [{'nickname': p.get('category', ''), 'rating': to_float(p.get('value'))} for p in points]

    @staticmethod
    def _maps(r) -> tuple[dict, list[dict]]:
        series, maps = {}, []
        for tile in r.select('.stats-match-maps a.stats-match-map'):
            href = tile.get('href') or ''
            score = Stats._two((tile.select_one('.stats-match-map-result-score') or tile).get_text())[:2]
            score = (score + [0, 0])[:2]
            name = tile.select_one('.dynamic-map-name-full')
            logo = tile.select_one('.stats-match-map-winner-logo')
            entry = {'map': name.get_text(strip=True) if name else '', 'score1': score[0], 'score2': score[1],
                     'winner': logo.get('title', '') if logo else '', 'selected': 'inactive' not in tile.get('class', [])}
            if 'mapstatsid' in href:
                maps.append({'stats_id': Stats._id(href, 'mapstatsid'), **entry, 'href': href})
            else:
                series = {'format': entry['map'], 'score1': score[0], 'score2': score[1], 'winner': entry['winner']}
        return series, maps

    # outcome icon -> (side of the winner, how the round ended)
    _OUTCOMES = {'ct_win': ('ct', 'elimination'), 't_win': ('t', 'elimination'), 'bomb_defused': ('ct', 'bomb_defused'),
                 'bomb_exploded': ('t', 'bomb_exploded'), 'stopwatch': ('ct', 'time')}

    @staticmethod
    def _rounds(r) -> tuple[list[dict], list[dict]]:
        """(per team rows, one merged list with a winner for every round)."""
        history = []
        for row in r.select('.round-history-team-row'):
            team = row.select_one('img.round-history-team')
            rounds, number, half = [], 0, 0
            for item in row.find_all(['div', 'img'], recursive=False):
                classes = item.get('class') or []
                if 'round-history-bar' in classes:
                    half += 1
                elif 'round-history-outcome' in classes:
                    number += 1
                    name = re.sub(r'\.\w+$', '', (item.get('src') or '').rsplit('/', 1)[-1])
                    side, reason = Stats._OUTCOMES.get(name, ('', ''))
                    score = [int(n) for n in re.findall(r'\d+', item.get('title') or '')][:2]
                    rounds.append({'round': number, 'half': max(half, 1), 'won': bool(side), 'outcome': name,
                                   'side': side, 'reason': reason, 'score': score})
            history.append({'team': team.get('title', '') if team else '', 'rounds': rounds})

        merged = []
        if len(history) == 2:
            for first, second in zip(history[0]['rounds'], history[1]['rounds']):
                winner, row = (history[0]['team'], first) if first['won'] else (history[1]['team'], second)
                if not row['won']:
                    continue
                score = row['score']  # titles always read left team first
                merged.append({'round': first['round'], 'half': first['half'], 'winner': winner, 'side': row['side'],
                               'reason': row['reason'], 'score1': score[0] if len(score) == 2 else 0,
                               'score2': score[1] if len(score) == 2 else 0})
        return history, merged

    # ---------------------------------------------------------------- players

    @staticmethod
    def _player(tr) -> dict | None:
        link = tr.select_one('td.st-player a[href*="/stats/players/"]')
        if link is None:
            return None
        flag = tr.select_one('td.st-player img.flag')

        def text(cls, eco=None):
            selector = f'td.{cls}' + ('' if eco is None else '.eco-adjusted-data' if eco else '.traditional-data')
            cell = tr.select_one(selector)
            return cell.get_text(' ', strip=True) if cell else ''

        def pair(value):
            numbers = (Stats._two(value) + [0, 0])[:2]
            return numbers[0], numbers[1]

        kills, headshots = pair(text('st-kills', False))
        e_kills, _ = pair(text('st-kills', True))
        assists, flash = pair(text('st-assists'))
        deaths, traded = pair(text('st-deaths', False))
        e_deaths, _ = pair(text('st-deaths', True))
        op_k, op_d = pair(text('st-opkd', False))
        e_op_k, e_op_d = pair(text('st-opkd', True))
        return {
            'id': Stats._id(link.get('href'), 'players'),
            'nickname': link.get_text(strip=True),
            'country': flag.get('title', '') if flag else '',
            'rating': to_float(text('st-rating')),
            'kills': kills, 'headshots': headshots,
            'hs_percent': round(headshots / kills * 100, 1) if kills else 0.0,
            'assists': assists, 'flash_assists': flash,
            'deaths': deaths, 'traded_deaths': traded, 'kd_diff': kills - deaths,
            'adr': to_float(text('st-adr', False)),
            'kast': to_float(text('st-kast', False)),
            'swing': to_float(text('st-roundSwing')),
            'opening_kills': op_k, 'opening_deaths': op_d,
            'multi_kills': to_int(text('st-mks')),
            'clutches': to_int(text('st-clutches')),
            'e_kills': e_kills, 'e_deaths': e_deaths,
            'e_adr': to_float(text('st-adr', True)),
            'e_kast': to_float(text('st-kast', True)),
            'e_opening_kills': e_op_k, 'e_opening_deaths': e_op_d,
        }

    @staticmethod
    def _players(r) -> dict[str, dict[str, list[dict]]]:
        """{team name: {'both': [...], 'ct': [...], 't': [...]}} from the six tables of a page."""
        teams: dict[str, dict[str, list[dict]]] = {}
        for table in r.select('table.stats-table'):
            classes = table.get('class', [])
            side = 'ct' if 'ctstats' in classes else 't' if 'tstats' in classes else 'both'
            head = table.select_one('th.st-teamname')
            name = head.get_text(strip=True) if head else ''
            rows = [p for p in (Stats._player(tr) for tr in table.select('tbody tr')) if p]
            teams.setdefault(name, {})[side] = rows
        return teams

    # ---------------------------------------------------------------- public

    def get_stats_page(self, r) -> dict[str, Any]:
        """Parse an overview (all maps) or single map statistics page."""
        info = r.select_one('.match-info-box')
        event_link = info.select_one('a[href*="/stats?event="]') if info else None
        series, maps = self._maps(r)

        team1 = self._team_box(info.select_one('.team-left') if info else None)
        team2 = self._team_box(info.select_one('.team-right') if info else None)

        by_team = self._players(r)
        names = list(by_team)
        for position, team in enumerate((team1, team2)):
            name = team['name'] if team['name'] in by_team else (names[position] if position < len(names) else '')
            sides = by_team.get(name, {})
            players = []
            for row in sides.get('both', []):
                row = dict(row)
                for side in ('ct', 't'):
                    row[side] = next((p for p in sides.get(side, []) if p['id'] == row['id']), None)
                players.append(row)
            team['players'] = players

        round_history, rounds = self._rounds(r)
        return {
            'event': {'id': to_int(re.search(r'event=(\d+)', event_link.get('href', '')).group(1)) if event_link else 0,
                      'title': event_link.get_text(strip=True) if event_link else ''},
            **self._when(info),
            'map': self._map_name(info),
            'team1': team1,
            'team2': team2,
            'series': series,
            'summary': self._summary(r),
            'top_players': self._top_players(r),
            'performance': self._performance(r),
            'round_history': round_history,
            'rounds': rounds,
            'maps': maps,
        }
