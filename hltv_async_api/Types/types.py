class Map:
    def __init__(self, mapname: str, r_team1: str, r_team2: str):
        self.mapname = mapname
        self.r_team1 = r_team1
        self.r_team2 = r_team2

    def __repr__(self):
        return f"Map(mapname={self.mapname}, r_team1={self.r_team1}, r_team2={self.r_team2})"

class PlayerStats:
    def __init__(self, player_id: str, nickname: str, kd: str, adr: str, rating: str):
        self.player_id = player_id
        self.nickname = nickname
        self.kd = kd
        self.adr = adr
        self.rating = rating

    def __repr__(self):
        return f"PlayerStats(player_id={self.player_id}, nickname={self.nickname}, kd={self.kd}, adr={self.adr}, rating={self.rating})"

class Match:
    def __init__(self, match_id: int, score_team1: str, score_team2: str, status: str, maps: list, players: list):
        self.match_id = match_id
        self.score_team1 = score_team1
        self.score_team2 = score_team2
        self.status = status
        self.maps = [Map(**m) for m in maps]
        self.players = [PlayerStats(**p) for p in players]

    def __repr__(self):
        return f"Match(match_id={self.match_id}, score_team1={self.score_team1}, score_team2={self.score_team2}, status={self.status}, maps={self.maps}, players={self.players})"

# Example usage
maps_data = [
    {'mapname': 'Overpass', 'r_team1': '10', 'r_team2': '13'},
    {'mapname': 'Nuke', 'r_team1': '6', 'r_team2': '13'},
    {'mapname': 'Mirage', 'r_team1': '-', 'r_team2': '-'}
]

players_data = [
    {'id': '18850', 'nickname': 'Jimpphat', 'kd': '33-29', 'adr': '80.9', 'rating': '1.08'}
    # Add more player data as needed
]

match = Match(
    match_id=2370931,
    score_team1='0',
    score_team2='2',
    status='Match over',
    maps=maps_data,
    players=players_data
)

print(match)
