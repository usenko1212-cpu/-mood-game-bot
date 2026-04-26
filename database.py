"""
База игр через внешние API:
  1. RAWG (https://rawg.io/apidocs)       — 500k+ игр, нужен бесплатный ключ
  2. FreeToGame (https://freetogame.com)  — бесплатные игры, без ключа

Логика:
  - mood → жанры/теги → запрос к API → фильтрация → список игр
  - Кеш в памяти (TTL 10 минут) чтобы не спамить API
"""

import os
import time
import logging
import httpx

logger = logging.getLogger(__name__)

# ─── Ключи ────────────────────────────────────────────────────────────────────
RAWG_API_KEY = os.getenv("RAWG_API_KEY", "")   # Получить бесплатно: https://rawg.io/apidocs
RAWG_BASE = "https://api.rawg.io/api"
FTG_BASE  = "https://www.freetogame.com/api"

# ─── Кеш ──────────────────────────────────────────────────────────────────────
_cache: dict = {}
CACHE_TTL = 600  # 10 минут


def _cache_get(key: str):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _cache_set(key: str, data: list) -> None:
    _cache[key] = (data, time.time())


# ─── Маппинг настроений → параметры API ───────────────────────────────────────
MOOD_TO_RAWG = {
    "relaxed":   {"genres": "simulation,puzzle,adventure", "tags": "relaxing,atmospheric,story-rich"},
    "energetic": {"genres": "action,shooter,fighting",     "tags": "action,fast-paced,arcade"},
    "sad":       {"genres": "adventure,indie",              "tags": "story-rich,atmospheric,emotional"},
    "social":    {"genres": "sports,racing,fighting",       "tags": "multiplayer,co-op,online-pvp"},
    "challenge": {"genres": "rpg,strategy,puzzle",          "tags": "difficult,roguelike,strategy"},
    "casual":    {"genres": "casual,arcade,puzzle",         "tags": "casual,family-friendly,2d"},
}

MOOD_TO_FTG = {
    "relaxed":   "strategy",
    "energetic": "shooter",
    "sad":       "mmorpg",
    "social":    "battle-royale",
    "challenge": "strategy",
    "casual":    "casual",
}

MOOD_WHY = {
    "relaxed":   "Успокаивает и даёт отдохнуть без стресса",
    "energetic": "Даст выброс адреналина и позволит выпустить пар",
    "sad":       "Погружает в историю и помогает отвлечься",
    "social":    "Весело играть вместе с другими",
    "challenge": "Бросает вызов и заставляет думать",
    "casual":    "Легко войти, не требует много времени",
}


# ─── RAWG ─────────────────────────────────────────────────────────────────────
async def fetch_rawg(mood: str) -> list:
    if not RAWG_API_KEY:
        logger.warning("RAWG_API_KEY не задан — пропускаем RAWG")
        return []

    cache_key = f"rawg_{mood}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = MOOD_TO_RAWG.get(mood, {})
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{RAWG_BASE}/games",
                params={
                    "key":        RAWG_API_KEY,
                    "genres":     params.get("genres", ""),
                    "tags":       params.get("tags", ""),
                    "ordering":   "-rating",
                    "page_size":  20,
                    "metacritic": "70,100",
                }
            )
            resp.raise_for_status()
            raw = resp.json().get("results", [])
    except Exception as e:
        logger.error(f"RAWG error: {e}")
        return []

    why = MOOD_WHY.get(mood, "")
    games = []
    for g in raw:
        platforms = ", ".join(
            p["platform"]["name"] for p in (g.get("platforms") or [])[:4]
        )
        genres = ", ".join(
            gen["name"] for gen in (g.get("genres") or [])[:3]
        )
        games.append({
            "title":        g.get("name", "—"),
            "genre":        genres or "—",
            "description":  f"Рейтинг: {g.get('rating', '?')}/5 • Вышла: {g.get('released', '—')}",
            "session_time": "Зависит от игры",
            "why":          why,
            "platform":     platforms or "—",
            "source":       "RAWG",
            "url":          f"https://rawg.io/games/{g.get('slug', '')}",
        })

    _cache_set(cache_key, games)
    return games


# ─── FreeToGame ───────────────────────────────────────────────────────────────
async def fetch_freetogame(mood: str) -> list:
    cache_key = f"ftg_{mood}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    category = MOOD_TO_FTG.get(mood, "mmorpg")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{FTG_BASE}/games",
                params={"category": category, "sort-by": "relevance"},
                headers={"User-Agent": "MoodGameBot/1.0"}
            )
            resp.raise_for_status()
            raw = resp.json()
    except Exception as e:
        logger.error(f"FreeToGame error: {e}")
        return []

    why = MOOD_WHY.get(mood, "")
    games = []
    for g in raw[:15]:
        games.append({
            "title":        g.get("title", "—"),
            "genre":        g.get("genre", "—"),
            "description":  (g.get("short_description") or "")[:120],
            "session_time": "Бесплатно играть",
            "why":          why,
            "platform":     g.get("platform", "—"),
            "source":       "FreeToGame",
            "url":          g.get("game_url", ""),
        })

    _cache_set(cache_key, games)
    return games


# ─── Главная функция ──────────────────────────────────────────────────────────
async def get_games_by_mood(mood: str, count: int = 3) -> list:
    """
    Возвращает `count` игр для заданного настроения.
    Порядок: RAWG → FreeToGame → локальный fallback
    """
    import random

    games = []

    rawg_games = await fetch_rawg(mood)
    if rawg_games:
        random.shuffle(rawg_games)
        games.extend(rawg_games[:count])

    if len(games) < count:
        ftg_games = await fetch_freetogame(mood)
        random.shuffle(ftg_games)
        games.extend(ftg_games[:count - len(games)])

    if not games:
        logger.warning(f"Оба API недоступны, fallback для mood={mood}")
        games = _local_fallback(mood)

    return games[:count]


# ─── Локальный fallback ───────────────────────────────────────────────────────
_FALLBACK = {
    "relaxed": [
        {"title": "Stardew Valley",    "genre": "Симулятор",     "description": "Уютная ферма без стресса",          "session_time": "30 мин+",  "why": "Успокаивает",        "platform": "PC/Mobile",  "source": "local", "url": ""},
        {"title": "Animal Crossing",   "genre": "Симулятор",     "description": "Строй остров своей мечты",          "session_time": "Любое",    "why": "Без давления",       "platform": "Switch",     "source": "local", "url": ""},
    ],
    "energetic": [
        {"title": "DOOM Eternal",      "genre": "Шутер",         "description": "Брутальный адреналиновый экшен",   "session_time": "30 мин+",  "why": "Выброс энергии",     "platform": "PC/Console", "source": "local", "url": ""},
        {"title": "Hades",             "genre": "Roguelike",     "description": "Пробивайся из подземного царства", "session_time": "30 мин+",  "why": "Адреналин+сюжет",    "platform": "PC/Console", "source": "local", "url": ""},
    ],
    "sad": [
        {"title": "Journey",           "genre": "Медитативное",  "description": "Красивое путешествие через пустыню","session_time": "2–3 ч",   "why": "Прожить эмоции",     "platform": "PC/PS4",     "source": "local", "url": ""},
        {"title": "Gris",              "genre": "Арт-платформер","description": "История о горе и возрождении",     "session_time": "3–5 ч",   "why": "Красота грусти",     "platform": "PC/Switch",  "source": "local", "url": ""},
    ],
    "social": [
        {"title": "It Takes Two",      "genre": "Кооп",          "description": "Лучший кооп для двоих",           "session_time": "2–4 ч",   "why": "Сближает",           "platform": "PC/Console", "source": "local", "url": ""},
        {"title": "Among Us",          "genre": "Дедукция",      "description": "Найди предателя на корабле",      "session_time": "15 мин",  "why": "Веселье в компании", "platform": "PC/Mobile",  "source": "local", "url": ""},
    ],
    "challenge": [
        {"title": "Elden Ring",        "genre": "Action RPG",    "description": "Огромный мир, жёсткие боссы",     "session_time": "1–4 ч",   "why": "Настоящий вызов",    "platform": "PC/Console", "source": "local", "url": ""},
        {"title": "Celeste",           "genre": "Платформер",    "description": "Сложный платформер с сюжетом",    "session_time": "2–10 ч",  "why": "Вызов + эмоции",     "platform": "PC/Console", "source": "local", "url": ""},
    ],
    "casual": [
        {"title": "Vampire Survivors", "genre": "Автошутер",     "description": "Выживай от монстров без усилий",  "session_time": "15–30 мин","why": "Медитативно",        "platform": "PC/Mobile",  "source": "local", "url": ""},
        {"title": "Unpacking",         "genre": "Пазл",          "description": "Распаковывай вещи и создавай уют","session_time": "30 мин+",  "why": "Уютно и просто",     "platform": "PC/Console", "source": "local", "url": ""},
    ],
}


def _local_fallback(mood: str) -> list:
    import random
    games = _FALLBACK.get(mood, _FALLBACK["casual"]).copy()
    random.shuffle(games)
    return games
