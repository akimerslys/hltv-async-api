

# hltv-async-api un envoltorio **no oficial** asincrónico de la API de HLTV para Python.

# IMPORTANTE

HLTV está detrás de Cloudflare y a menudo responde con **403** a las peticiones HTTP normales. Ya hay disponible un **controlador indetectable de Selenium** opcional: consulta [Selenium (controlador indetectable)](#selenium-controlador-indetectable).

No olvides darle estrella al repositorio.

# Futuro

* **0.10.0** actualización de estadísticas e imágenes, más raspadores de estadísticas, logotipos de equipos, fotos de jugadores, imágenes, más datos, estadísticas de team_map, estadísticas de mapas, más funciones como get_news_id, get_team_logo, get_player_photo, get_demo_id, get_match_stats. Cobertura. (?) User agent rotativo

* **FUTURO** Cambio de requests a controlador Selenium && Datos en vivo con socket.io && Permitir usar Hltv-async-api en cualquier sistema y lenguaje, creando un servicio RESTful.


# Características


* **Uso sencillo** (es realmente simple)


* **Biblioteca totalmente asincrónica, nueva y moderna**


* **Gran cantidad de opciones y métodos**


* **Soporta el uso de proxies**


* **Hecho con amor <3**


---

# Instalación

```
pip install hltv-async-api
```

Extras opcionales:

```
pip install "hltv-async-api[sync]"      # cliente sincrónico (requests)
pip install "hltv-async-api[selenium]"  # controlador Chrome indetectable, úsalo cuando HLTV responda 403
pip install "hltv-async-api[live]"      # live match data over sockets
```

---


# Uso Sencillo

  ```
    
    from hltv_async_api import Hltv
    
    async def main():
      async with Hltv() as hltv:
        print(await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024'))
        
    if __name__ == '__main__':
      import asyncio
      asyncio.run(main())

  ```


# Uso Sincrónico (Beta)

  _Para un uso de alto rendimiento, se recomienda usar la versión asincrónica, es 5x más rápida y más estable._

  ```
  
    from hltv_async_api.sync import Hltv
    
    hltv = Hltv()

    print(hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024'))
  
  ```


---

# Selenium (controlador indetectable)

HLTV protege sus páginas con Cloudflare, por lo que las peticiones HTTP normales suelen fallar con `403`. Cuando
ocurre, la biblioteca muestra una sola vez este aviso (en inglés):

```
[ERROR] | HLTV answered 403 / Cloudflare challenge, plain HTTP requests are being blocked. Install the optional browser
driver with: pip install "hltv-async-api[selenium]" and create the client with Hltv(selenium=True).
```

El controlador opcional abre una ventana real de Chrome con [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
y lee las páginas desde ella. Todos los métodos conservan el mismo nombre, argumentos y resultado; solo cambia la forma de obtener las páginas.

**Requisitos**

* Google Chrome instalado en el equipo.
* `pip install "hltv-async-api[selenium]"`. En la primera ejecución undetected-chromedriver descarga un ChromeDriver
  compatible con tu versión de Chrome.

**Uso asíncrono**

```
import asyncio
from hltv_async_api import Hltv


async def main():
    async with Hltv(selenium=True) as hltv:   # el navegador se cierra al terminar el bloque
        print(await hltv.get_top_teams(5))
        print(await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen2024'))


if __name__ == '__main__':
    asyncio.run(main())
```

**Uso sincrónico**

```
from hltv_async_api.sync import Hltv

with Hltv(selenium=True) as hltv:
    print(hltv.get_top_teams(5))
```

Sin `with`, llama a `await hltv.close()` (asíncrono) o `hltv.close()` (sincrónico) al terminar; si no, Chrome queda abierto.

**Opciones**

Pásalas como diccionario en `selenium_options`:

```
hltv = Hltv(selenium=True, selenium_options={
    'headless': False,                 # Cloudflare detecta más a menudo Chrome sin ventana, por eso el valor por defecto es False
    'version_main': 130,               # fuerza el ChromeDriver de esta versión principal de Chrome
    'challenge_timeout': 30,           # segundos de espera a que termine por sí sola la verificación de Cloudflare
    'page_load_timeout': 30,           # segundos de espera a que cargue una página
    'proxy': 'http://1.2.3.4:8080',
    'user_data_dir': './chrome-profile',   # conserva la cookie de Cloudflare entre ejecuciones
    'pool_size': 4,                    # ventanas de Chrome trabajando en paralelo (por defecto 1)
    'page_load_strategy': 'eager',     # 'normal' espera también a anuncios y rastreadores
})
```

**Conviene saber**

* Un navegador carga una página a la vez. Define `pool_size` (por ejemplo `selenium_options={'pool_size': 4}`) para usar varias
  ventanas de Chrome en paralelo; `asyncio.gather` obtendrá entonces ese número de páginas a la vez. Cada ventana es un Chrome
  completo, cuida la RAM. Con `user_data_dir` cada ventana usa su propia copia (`<dir>-1`, `<dir>-2`, ...).
* `page_load_strategy` es `'eager'` por defecto: la página se lee en cuanto su HTML está listo, sin esperar a todos los anuncios y
  rastreadores, lo que es mucho más rápido. Usa `'normal'` para esperar todo.
* Se respeta `max_retries` (3 intentos si vale `0`). `min_delay`, `max_delay`, `max_concurrency` y las opciones de proxy del cliente HTTP
  no se usan en este modo; usa `pool_size` y `proxy` en `selenium_options`.
* No garantiza el acceso: Cloudflare cambia sus comprobaciones con frecuencia. Si una página no pasa, el método
  devuelve `None` y registra `Connection failed`. Prueba con `user_data_dir`, otra `version_main` o una IP limpia.
* Si el ChromeDriver descargado no coincide con tu Chrome (`This version of ChromeDriver only supports Chrome version X`), la
  biblioteca lee tu versión de Chrome del error y reintenta con un controlador compatible. También puedes fijar `version_main`.
* Si falta el extra, `Hltv(selenium=True)` lanza un `ImportError` indicando qué instalar.
* Úsalo con responsabilidad y respeta los términos y el `robots.txt` de HLTV. La biblioteca es para uso no comercial.

---

# Datos en vivo (sockets)

El marcador en vivo de HLTV usa un "scorebot" Socket.IO. El extra opcional `live` se conecta a él:

```bash
pip install "hltv-async-api[live]"      # o: pip install -r requirements-live.txt
```

Instantánea de un partido en vivo (devuelve `None` si no está en vivo o no llegó nada en `timeout`):

```python
data = await hltv.get_match_data(2400302, timeout=15)
# {'match_id': ..., 'score': {'wins': {...}, 'maps': [...], 'current_map': {...}}, 'scoreboard': <raw>, 'log': [...]}
```

Actualizaciones continuas:

```python
live = await hltv.live_match(2400302, on_event=lambda event, data: print(event, data))
async for event, data in live.updates():
    ...
await live.close()   # hltv.close() también lo hace
```

* Los eventos `score` se interpretan; `scoreboard`, `log` y `fullLog` se entregan tal cual los envía el socket.
* Opciones extra (`cookies`, `user_agent`) van a `hltv_async_api.live.LiveMatch`.
* La librería no intenta evadir ninguna protección anti-bots. Si falta el extra, se lanza un `ImportError` claro.

# Configuración

* max_delay: float | None = None

  No se espera nada entre reintentos salvo que definas `min_delay` / `max_delay`. Con solo `max_delay` la pausa crece 1 seg
  por intento fallido hasta ese valor:

  ```
    hltv = Hltv(max_delay=5)

    >>>Fetching https://www.hltv.org/matches/2370727/faze-vs-natus-vincere-pgl-cs2-major-copenhagen-2024, code: 403
    >>>Increasing delay to 1s
    >>>Fetching https://www.hltv.org/matches/2370727/faze-vs-natus-vincere-pgl-cs2-major-copenhagen-2024, code: 403
    >>>Increasing delay to 2s
  ```

* min_delay: float | None = None

  Espera un tiempo aleatorio entre `min_delay` y `max_delay` antes de cada reintento.

```
  [DEBUG] Random delay 9.55s
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 3/10
  [DEBUG] Random delay 3.9s
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 4/10
```

* max_concurrency: int = 10

  Cuántas peticiones pueden estar en curso a la vez. `0` quita el límite. Lanza tus llamadas juntas para aprovecharlo:

  ```
  teams = await hltv.get_top_teams(30)
  infos = await asyncio.gather(*(hltv.get_team_info(t['id'], t['title']) for t in teams))
  ```
  Súbelo para ir más rápido, bájalo si HLTV responde 429 / 403.

* proxy_delay: bool = False

    Retraso para el uso de proxies.
* 
  ```
  [INFO] New proxy: http://123.123.123.123:123 
  [DEBUG] Random delay 9.55s 
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 3/10
  [DEBUG] Switching proxy http://123.123.123.123:123 
  [INFO] New proxy: http://111.111.111.11:111 
  [DEBUG] Random delay 3.9s 
  [DEBUG] Trying connect to https://www.hltv.org/matches, try 4/10
  ```

* max_retries: int = 10

    0 para reintentos infinitos
    
    ```
    hltv = Hltv(max_retries=2, debug=True)
    print(await hltv.get_top_players())
    
    >>>Creating Session
    >>>Trying connect to https://www.hltv.org/stats/players?startDate=2024-01-01&endDate=2024-12-31&rankingFilter=Top20, try 1/2
    >>>Trying connect to https://www.hltv.org/stats/players?startDate=2024-01-01&endDate=2024-12-31&rankingFilter=Top20, try 2/2
    >>>Connection failed
    ```

* proxy_list: list | None = None

    Proxies. _len(proxy_list) >= 1_
    Nota: Para agregar un elemento sin proxy a la lista, simplemente pon '' en su lugar. Puedes encontrar una plantilla en los ejemplos.

* proxy_path: str | None = None

    Ruta a tu archivo de proxies (proxy_list será ignorado). Un proxy por línea.

* proxy_protocol: str | None = None,

    Protocolo de proxy. Tus proxies ```hltv = Hltv(proxy_protocol='http' ...) -> '11.11.11.11:1111' -> 'http://11.11.11.11:1111'

* remove_proxy: bool = False

    Elimina el proxy de la lista si la conexión falla (incluye proxy_path)

* timeout: int = 5

    Tiempo de espera para la conexión en segundos.

* debug: bool = False

* tz: str = 'Europe/Copenhagen':
    
    Configuración de zona horaria. 
 
    <a href='https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568'>Haz clic aquí </a> para ver todas las zonas horarias disponibles

* safe_mode: bool = False

    Opcional. Con `True` se bloquean los métodos que devuelven datos restringidos (`get_matches`, `get_match_info`, `get_results`, `get_top_players`, `get_match_data`, `live_match`)
    y devuelven `None`. Por defecto no se bloquea nada.

* aiohttp_session: aiohttp.ClientSession | None = None

    Sesión personalizada de aiohttp, si deseas usar tu propia sesión.

* selenium: bool = False

    Obtiene las páginas con un controlador Chrome indetectable en lugar de peticiones HTTP normales. Requiere `pip install "hltv-async-api[selenium]"`, consulta [Selenium (controlador indetectable)](#selenium-controlador-indetectable).

* selenium_options: dict | None = None

    Opciones del controlador de Selenium: `headless`, `version_main`, `challenge_timeout`, `page_load_timeout`, `proxy`, `user_data_dir`, `pool_size`, `page_load_strategy`.

---

# Uso de Proxy

**Cargar proxies desde una lista**
    
    ```
    proxy_list = ['http://120.234.203.171:9002', 'http://110.38.68.38:80']
    
    hltv = Hltv(proxy_list=proxy_list)

    ```

**Cargar proxies desde un archivo**

    ```
    hltv = Hltv(proxy_path='PATH_TO_PROXY.TXT')
    ```


**Eliminar proxy**

    Elimina los proxies defectuosos
    
    ```
    hltv = Hltv(proxy_path='PATH_TO_PROXY.TXT', remove_proxy=True)
    ```

**Uso de protocolo**

    ```
    proxy_list = ['120.234.203.171:9002', '110.38.68.38:80']
    
    hltv = Hltv(proxy_list=proxy_list, proxy_protocol='http')
    ```

---

# Métodos

Todos los ids, resultados, posiciones y contadores se devuelven como número (`int`); ratings / ADR / edad / porcentaje de
headshots como `float`. Los campos que pueden ser texto siguen siendo texto: nombres, fechas, `status`, `prize`,
`team_count` (puede ser `'TBA'`), `kd` (`'33-29'`) y `posted` (`'an hour ago'`). Un valor aún no disponible es `0` / `0.0`,
nunca `'-'` ni `''`.

* **get_matches(days: int = 1, min_rating: int = 1, live: bool = True, future: bool = True)**

    -days (número de días hacia el futuro)

    -min_rating (calificación mínima de estrellas)

    ```
    await hltv.get_matches(days=1, min_rating=3)

    >>> [{'id': 2399417, 'date': 'LIVE', 'time': 'LIVE', 'team1': 'FURIA', 'team2': 'BETBOOM', 't1_id': 8297, 't2_id': 12394, 'maps': 5, 'rating': 4, 'event': 'Thunderpick World Championship 2026'}]
    ```
    `maps` es el best-of (`0` si se desconoce), `date` es `'dd-mm-yyyy'` y `t1_id` / `t2_id` son `0` para equipos `TBD`.

* **get_match_info(match_id: int | str, team1, team2, event_title, stats: bool = True, predicts: bool = True)**

    ```
    await hltv.get_match_info(2373774, 'Astralis', 'Falcons', 'BLAST Premier Fall Groups 2024')

    >>> {'id': 2373774, 'status': 'Match over',
         'maps': [{'mapname': 'Dust2', 'r_team1': 13, 'r_team2': 7, 'pick': 'Falcons'},
                  {'mapname': 'Ancient', 'r_team1': 13, 'r_team2': 9, 'pick': 'Astralis'},
                  {'mapname': 'Nuke', 'r_team1': 0, 'r_team2': 0, 'pick': ''}],
         'stats': [{'id': 17956, 'nickname': 'jabbi', 'kd': '42-30', 'adr': 91.6, 'rating': 1.43}, ...],
         'score1': 2, 'score2': 0}
    ```
    `status` es `'Match over'`, `'LIVE'` o la hora de inicio (`'dd-mm-yyyy-HH-MM'`) de un partido próximo, que además recibe
    `predict1` / `predict2` (probabilidad de victoria en porcentaje, `int`). `r_team1` / `r_team2` son `0` mientras el mapa no se juega.

* **get_results(days: int = 1, min_rating: int = 1, max: int = 30, featured: bool = True, regular: bool = True)**

    ```
    await hltv.get_results(days=1, min_rating=3, max=1)

    >>> [{'id': 2400004, 'team1': 'Natus Vincere', 'team2': 'Falcons', 'score1': 2, 'score2': 1, 'rating': 3, 'event': 'IEM Beijing 2026'}]
    ```

* **get_events(outgoing: bool = True, future: bool = True, max_events: int = 10)**

    ```
    await hltv.get_events(max_events=2)

    >>> [{'id': 9407, 'title': '1win Private Club Season 2', 'start_date': '19-10', 'end_date': '22-10'}, ...]
    ```

* **get_event_results(event_id: int | str, days: int = 1, max_: int = 10)**

    ```
    await hltv.get_event_results(7148)

    >>> [{'id': 2370727, 'date': '31-03-2024', 'team1': 'FaZe', 'team2': 'Natus Vincere', 'score1': 1, 'score2': 2}]
    ```

* **get_event_matches(event_id: int | str, days: int = 1, max_: int = 10)**

    ```
    await hltv.get_event_matches(7148)

    >>> [{'id': 2399417, 'date': 'LIVE', 'team1': 'FURIA', 'team2': 'BETBOOM', 't1_id': 8297, 't2_id': 12394},
         {'id': 2370771, 'date': '2024-04-18', 'time': '15:30', 'team1': 'Monte', 'team2': 'paiN', 't1_id': 11811, 't2_id': 4773}]
    ```

* **get_event_info(event_id: int | str, event_title: str)**

    ```
    await hltv.get_event_info(7148, 'PGL CS2 Major Copenhagen 2024')

    >>> {'id': 7148, 'title': 'PGL CS2 Major Copenhagen 2024', 'start': '21-03-2024', 'end': '31-03-2024', 'status': 'Finished',
         'prize': '$1,250,000', 'team_count': '16', 'location': 'Copenhagen, Denmark',
         'mvp': {'id': 19206, 'nickname': 'jL'},
         'winners': [{'place': 1, 'team': 'Natus Vincere', 'id': 4608, 'prize': '$500,000'}, ...]}
    ```
    `status` es `'Finished'`, `'Ongoing'` o `'Upcoming'`. Los eventos terminados tienen `mvp` y `winners`; los demás
    tienen `teams`: `[{team_id: 'nombre'}, ...]`.

* **get_top_teams(max_teams: int = 30, date_str: str = '')**

    ```
    await hltv.get_top_teams(2)

    >>> [{'id': 7020, 'rank': 1, 'title': 'Spirit', 'points': 904, 'change': 0}, {'id': 9565, 'rank': 2, 'title': 'Vitality', 'points': 898, 'change': 0}]
    ```
    `change` son los puestos que se movió desde el ranking anterior (`+3` -> `3`, `-1` -> `-1`, `0` si no cambió).

* **get_team_info(team_id: int | str, title: str)**

    ```
    await hltv.get_team_info(6667, 'faze')

    >>> {'id': 6667, 'title': 'faze', 'rank': 17, 'players': {'frozen': 9960, 'Twistzz': 10394}, 'coach': 'enkay J', 'age': 23.3, 'weekstop30': 56, 'last_trophy': 'IEM Chengdu 2024', 'total_trophies': 22}
    ```

* **get_last_news(max_reg_news: int = 2, only_today: bool = True, only_featured: bool = False)**

    ```
    await hltv.get_last_news(only_today=True)

    >>> [{'date': '07-11', 'f_news': [], 'news': [{'id': 45914, 'title': 'IEM Beijing 2026 playoff bracket set', 'posted': 'an hour ago'}]}]
    ```

* **get_top_players(top: int = 40, year: int | str | None = None)**

    ```
    await hltv.get_top_players(2)

    >>> [{'id': 11893, 'rank': 1, 'nickname': 'ZywOo', 'team': 'Vitality', 'maps': 1572, 'rating': 1.27}, {'id': 21167, 'rank': 2, 'nickname': 'donk', 'team': 'Spirit', 'maps': 673, 'rating': 1.25}]
    ```

* **get_player_info(id: int | str, nickname: str)** - página de perfil (`/player/<id>/<nickname>`)

    Con la nueva interfaz devuelve además: `born`, `prize_money`, `top20` (puesto y año), `rating_top_percent` / `rating_percentile`,
    `stats_period` / `stats_maps` (ventana de las estadísticas, p. ej. "Past 3 months", 72 mapas), `roles` (firepower, entrying, trading, opening,
    closing, sniping, utility de 0 a 100), `socials`, `upcoming_matches` y `recent_matches`. `recent_matches[...]['stats_id']` sirve directamente
    para [get_match_stats](#métodos). `last_matches` conserva la lista plana anterior.
    Ejemplo completo en la [sección en inglés](README.md#methods).

## Estadísticas de jugadores

Páginas de `hltv.org/stats/players/...`. Todos los métodos aceptan los mismos **filtros** opcionales como argumentos con nombre:

| argumento | valores |
|---|---|
| `cs_version` | `'CS2'` (por defecto), `'CSGO'`, `None` = ambos |
| `map` | `'mirage'`, `'de_nuke'`, ... |
| `match_type` | `'majors'`, `'big_events'`, `'mvp_events'`, `'lan'`, `'online'` |
| `start_date` / `end_date` | `'YYYY-MM-DD'`; `start_date='all'` = sin límite de fecha |
| `ranking` | `5`, `10`, `20`, `30`, `50` (solo partidos contra el top N) |
| `best_of` | `1`, `3`, `5` |
| `ranked` | `True` / `False` (eventos clasificados por Valve) |
| `playoff` | `'grand_final'`, `'playoffs'`, `'pre_playoff'` |
| `team_id`, `opponent_team`, `event` | solo partidos de / contra este equipo, o en este evento |

Las tablas muestran 100 filas; cada resultado trae `pagination` (`{'from': 1, 'to': 100, 'total': 574}`): usa `offset=100` para la siguiente página.
Cada resultado incluye también `player_id` y la `url` de origen.

* **get_player_stats(player_id, nickname, \*\*filters)** - resumen: `summary` (rating, t_rating, ct_rating, round_swing, dpr, kast, multi_kill, adr, kpr),
  `roles` (los siete roles con su puntuación total, CT y T, y cada métrica con `value`, `ct`, `t` y `band`), `similar_players`, `featured_ratings` (rating contra top 5-50) y `teammates`.
  Los tiempos son segundos y los porcentajes números simples.
* **get_player_advanced(player_id, nickname, \*\*filters)** - round swing, impacto, duelos, ronda a ronda y mapa a mapa (`headline`, `sections`).
* **get_player_matches(player_id, nickname, offset=0, \*\*filters)** - cada mapa jugado (`stats_id`, fecha, equipos y marcador, mapa, kills, deaths, rating, `won`) y `summary`.
* **get_player_events(player_id, nickname, \*\*filters)** - eventos jugados: puesto, mapas, KPR / DPR, diferencia y rating.
* **get_player_career(player_id, nickname, \*\*filters)** - rating y mapas por año: total, online, LAN y majors.
* **get_player_weapons(player_id, nickname, \*\*filters)** - kills por tipo de arma, armas llevadas y kills por arma.
* **get_player_clutches(player_id, nickname, size='all', offset=0, \*\*filters)** - historial de clutches; `size`: `'all'` o `1`-`5`.
* **get_player_multikills(player_id, nickname, kills=2, fast=False, offset=0, \*\*filters)** - historial de multikills; `kills`: `'all'` o `2`-`5`; `fast=True` solo multikills rápidas.
* **get_player_opponents(player_id, nickname, \*\*filters)** - resultados contra cada equipo.
* **get_player_full_stats(player_id, nickname, \*\*filters)** - resumen, avanzadas, partidos, eventos, carrera y armas en una llamada (en paralelo); una página que no se pudo cargar es `None`.

El cliente sync tiene los mismos métodos. Comprobado con páginas reales: las vistas por defecto, un filtro de mapa, `offset`, clutches `1 on 3`,
multikills `3x` y `fast=True`. La página de un solo tamaño de clutch oculta las cajas de derrotas y diferencia (`losses` y `difference` son `None`).
Los demás filtros y tamaños usan el esquema de URL de HLTV pero no se capturaron: si alguno devuelve una forma inesperada, abre un issue con la página.
Estructura completa de cada respuesta en la [sección en inglés](README.md#methods).

## Estadísticas de partidos

* **get_match_stats(stats_id: int | str, team1: str = 'team', team2: str = 'team')**

    Estadísticas detalladas de un partido **terminado** (`hltv.org/stats/matches/<stats_id>/...`): el resumen de todos los mapas y,
    obtenidas en paralelo, la página de cada mapa. `stats_id` es el campo `stats_id` de `get_match_info`; los nombres de los
    equipos solo construyen la URL y son opcionales.

    ```
    info = await hltv.get_match_info(2400009, 'MOUZ', 'BETBOOM', 'IEM Beijing 2026')
    # info['stats_id'] == 132835, info['maps'][0]['stats_id'] == 243791 (0 si aún no hay estadísticas)

    stats = await hltv.get_match_stats(info['stats_id'], 'MOUZ', 'BETBOOM')
    ```
    Devuelve evento, fecha, `team1` / `team2` con su lista `players` (rating, kills, headshots, `hs_percent`, assists,
    deaths, ADR, KAST, swing, aperturas, multi-kills, clutches, valores ajustados por economía `e_*` y los mismos campos por lado en
    `ct` / `t`), `summary`, `top_players`, `performance` y `maps`: una entrada por mapa con sus propias estadísticas completas
    (`available` es `False` si su página no se pudo cargar). `round_history` (por equipo) y `rounds` (una entrada por ronda: ganador, lado, motivo `elimination` / `bomb_defused` / `bomb_exploded` / `time` y marcador)
    solo existen en las páginas de mapa, donde `summary['breakdown']` además da las mitades.
    Estructura completa en la [sección en inglés](README.md#methods).

* **get_map_stats(map_stats_id: int | str, team1: str = 'team', team2: str = 'team')**

    Un solo mapa, misma estructura sin `maps`.

* **get_stats_for_match(match_id, team1, team2, event_title)**

    `get_match_info` + `get_match_stats` en una llamada. `None` mientras el partido no tenga estadísticas.

* **get_match_data(match_id: int | str, timeout: float = 15)** / **live_match(match_id, on_event=None)**

    Datos en vivo por sockets, consulta [Datos en vivo](#datos-en-vivo-sockets).

* **get(type: str, id: int | str | None = None, title: str | None = None, team1: str | None = None, team2: str | None = None)**
  (BETA) Atajo a los métodos anteriores. Tipos: `'events'`, `'matches'`, `'news'`, `'teams'`.

---
# Ejemplos

****Ejemplo Sencillo****

```
from hltv_async_api import Hltv


async def test():

    async with Hltv() as hltv:
      print(await hltv.get_event_info(7148, 'pgl-cs2-major-copenhagen-2024'))

if __name__ == "__main__":
    asyncio.run(test())
```

****Raspeador con Proxy****

```
from hltv_async_api import Hltv


async def test():

    hltv = Hltv(debug=True, proxy_path='proxy_test.txt', timeout=1, remove_proxy=True, proxy_protocol='http')
    
    print(await hltv.get_event_info(7148, 'pgl-cs2-major-copenhagen-2024'))

if __name__ == "__main__":
    asyncio.run(test())
```

****Raspeador automático con arq y redis****

- para ejecutar escribe "arq PATH_TO_FILE.WorkerSettings"

    ```
    import ujson
    import asyncio
    from arq import cron
    from redis.asyncio import Redis, ConnectionPool
    
    from hltv_async_api import Hltv
    
    
    
    async def startup(ctx):
        async with Hltv(max_delay=5, proxy_path='proxies.txt', debug=True) as hltv:
              ctx["hltv"] = hltv
  
        ctx["redis"] = redis_client = Redis(
            connection_pool=ConnectionPool.from_url(settings.redis_url))
        logger.success(f"Scheduler started. UTC time {datetime.utcnow()}")
    
    
    async def shutdown(ctx):
        await ctx["redis"].close()
    
    
    async def parse_matches(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        matches = await hltv.get_upcoming_matches(1, 1)
        if matches:
            await redis.set("matches", ujson.dumps(matches))
        else:
            logger.error("error parsing matches")
    
    async def parse_events(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        events = await hltv.get_events()
        if events:
            await redis.set("events", ujson.dumps(events))
        else:
            logger.error("error parsing events")
    
    
    async def parse_top_teams(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        top_teams = await hltv.get_top_teams(30)
        if top_teams:
            await redis.set("top_teams", ujson.dumps(top_teams))
        else:
            logger.error("error parsing top teams")
    
    
    async def parse_top_players(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        top_players = await hltv.get_top_players(30)
        if top_players:
            await redis.set("top_teams", ujson.dumps(top_players))
        else:
            logger.error("error parsing top players")
    
    
    async def parse_last_news(ctx):
        hltv = ctx["hltv"]
        redis = ctx["redis"]
        news = await hltv.get_last_news(only_today=True, max_reg_news=4)
        if news:
            await redis.set("news", ujson.dumps(news))
        else:
            logger.error("error parsing news")
    
    
    class WorkerSettings:
        redis_settings = settings.redis_pool
        on_startup = startup
        on_shutdown = shutdown
        functions = [parse_matches,
                     parse_events,
                     parse_top_teams,
                     parse_top_players,
                     parse_last_news,
                     ]
        cron_jobs = [
            cron(parse_matches, minute=59),
            cron(parse_events, hour=0, minute=0, second=0),
            cron(parse_top_teams, day=0, hour=18, minute=1, second=30),
            cron(parse_top_players, day=0, hour=20, minute=0, second=0),
            cron(parse_last_news, minute=55),
        ]

    ```

# Pruebas:

**<a href='https://github.com/akimerslys/hltv-async-api/blob/main/test/hard_test.py'>Para probar la biblioteca puedes usar temporalmente este archivo de pruebas</a>**

```

Parsed 208 matches.(97s) ERRORS: 0/208
Parsed 25 events.(23s) ERRORS: 0/25
Parsed 31 teams.(41s) ERRORS: 0/31
Parsed 31 players.(28s) ERRORS: 0/31
ERRORS=0
SUCCESS=284
Total parsed=284
Total time 96.8368

```

# Beta / No lanzado

from hltv_async_api.beta import Beta

# Requisitos:

Python 3.10+

Licencia:
HLTV Async está licenciado bajo la Licencia MIT, permitiendo uso personal y comercial con restricciones mínimas.

# Contribuciones

¿Por qué no?
