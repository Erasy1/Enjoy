from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import math

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

#  Paths & App 
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"

app = Flask(__name__)
app.secret_key = "1d502d2e479b050729ebb07c8b1d0a34"  

#  TMDB Config 
load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

# DB 
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def jdump(x) -> str:
    return json.dumps(x, ensure_ascii=False)


def jload(s: str):
    try:
        return json.loads(s) if s else None
    except json.JSONDecodeError:
        return None

def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def jaccard(a: set[int], b: set[int]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def genre_id(name: str, media_type: str, lang: str = "ru-RU") -> Optional[int]:
    gm = get_genre_map(media_type, lang)
    return gm.get(name.strip().lower())


def build_genre_sets_for_signals(lang: str = "ru-RU") -> Dict[str, set[int]]:
    # Берём id жанров у TMDB для эвристик 
    # Если каких-то жанров нет, просто не добавятся
    def gid(n: str) -> Optional[int]:
        return genre_id(n, "movie", lang)

    def collect(names: List[str]) -> set[int]:
        out = set()
        for n in names:
            x = gid(n)
            if isinstance(x, int):
                out.add(x)
        return out

    return {
        "fast": collect(["боевик", "action", "триллер", "thriller", "приключения", "adventure", "криминал", "crime"]),
        "slow": collect(["драма", "drama", "романтика", "romance", "документальный", "documentary"]),
        "light": collect(["комедия", "comedy", "приключения", "adventure", "анимация", "animation", "семейный", "family"]),
        "tense": collect(["триллер", "thriller", "криминал", "crime", "ужасы", "horror", "детектив", "mystery"]),
        "inspiring": collect(["драма", "drama", "история", "history", "документальный", "documentary"]),
        "dark": collect(["ужасы", "horror", "триллер", "thriller", "криминал", "crime"]),
        "think": collect(["детектив", "mystery", "фантастика", "science fiction", "триллер", "thriller"]),
        "simple": collect(["комедия", "comedy", "семейный", "family", "анимация", "animation"]),
        "complex": collect(["детектив", "mystery", "триллер", "thriller", "фантастика", "science fiction"]),
    }


def signal_score(genre_ids: List[int], target_set: set[int]) -> float:
    s = set(int(x) for x in (genre_ids or []) if isinstance(x, int) or str(x).isdigit())
    return jaccard(s, target_set)


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS onboarding_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_key TEXT NOT NULL,
        answer TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, question_key),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # Тайтлы для 10 вопроса  
    cur.execute("""
    CREATE TABLE IF NOT EXISTS onboarding_titles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tmdb_id INTEGER NOT NULL,
        media_type TEXT NOT NULL,   -- movie / tv
        title TEXT NOT NULL,        -- cached title
        liked INTEGER NOT NULL,     -- 1=like, 0=dislike
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, tmdb_id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    #  Aggregated preferences for cold-start recommendations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,

        content_type TEXT NOT NULL,            -- movie | tv | both
        languages_json TEXT NOT NULL,          -- ["ru","en",...]
        audio_pref TEXT NOT NULL,              -- dub | subs | any

        liked_genres_json TEXT NOT NULL,       -- ["Action","Drama"] or ids as strings
        blocked_genres_json TEXT NOT NULL,     -- ["Horror",...]
        blocked_topics_json TEXT NOT NULL,     -- ["war","school",...]

        pace TEXT NOT NULL,                    -- fast | medium | slow
        mood TEXT NOT NULL,                    -- light | tense | inspiring | dark | think | mixed
        plot_complexity TEXT NOT NULL,         -- simple | medium | complex

        age_limit TEXT NOT NULL,               -- none | 16 | 18
        content_flags_json TEXT NOT NULL,      -- ["no_violence","no_18","no_drugs"] (optional)

        favorite_titles_json TEXT NOT NULL,    -- [{"tmdb_id":..,"media_type":"movie"},...]
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
        # Continue Watching,History
    cur.execute("""
    CREATE TABLE IF NOT EXISTS watch_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tmdb_id INTEGER NOT NULL,
        media_type TEXT NOT NULL,      -- movie / tv
        title TEXT NOT NULL,
        poster_url TEXT,
        progress INTEGER NOT NULL DEFAULT 0,  -- 0..100
        last_watched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, tmdb_id, media_type),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    
        # My List 
    cur.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tmdb_id INTEGER NOT NULL,
        media_type TEXT NOT NULL,      -- movie / tv
        title TEXT NOT NULL,
        poster_url TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, tmdb_id, media_type),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS my_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tmdb_id INTEGER NOT NULL,
        media_type TEXT NOT NULL,   -- movie / tv
        title TEXT NOT NULL,
        poster_url TEXT,
        status TEXT NOT NULL DEFAULT 'planning',  -- planning / archived
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, tmdb_id, media_type),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()


_db_inited = False
@app.before_request
def ensure_db():
    global _db_inited
    if not _db_inited:
        init_db()
        _db_inited = True


#  read onboarding answers 
def get_onboarding_answer(user_id: int, qkey: str) -> Optional[str]:
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT answer FROM onboarding_answers WHERE user_id=? AND question_key=?",
        (user_id, qkey)
    ).fetchone()
    conn.close()
    return row["answer"] if row else None


def get_onboarding_liked_titles(user_id: int) -> List[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT tmdb_id, media_type, title
        FROM onboarding_titles
        WHERE user_id=? AND liked=1
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _normalize_content_type(raw: str) -> str:
    # Step1: Фильмы,Сериалы,50–50 
    x = (raw or "").strip().lower()
    if "фильм" in x or x == "movie":
        return "movie"
    if "сериал" in x or x == "tv":
        return "tv"
    return "both"


def _normalize_audio_pref(raw: str) -> str:
    x = (raw or "").strip().lower()
    # Step2: Озвучк,Субтитры,Без разницы
    if "озвуч" in x or x == "dub":
        return "dub"
    if "суб" in x or x == "subs":
        return "subs"
    return "any"


def _normalize_pace(raw: str) -> str:
    # Step 3: Быстрый,Средный,Медленный
    x = (raw or "").strip().lower()
    if "динами" in x or x in ("fast", "dynamic"):
        return "fast"
    if "мед" in x or "атмос" in x or x == "slow":
        return "slow"
    return "medium"


def _normalize_mood(raw: str) -> str:
    # Step 4: Легкий,Напряженный,Вдохновлящий,Мрачный,Заставляущий подумать,Без разницы
    x = (raw or "").strip().lower()
    if "лёг" in x or "лег" in x or x == "light":
        return "light"
    if "напр" in x or x == "tense":
        return "tense"
    if "вдох" in x or x == "inspiring":
        return "inspiring"
    if "мрач" in x or x == "dark":
        return "dark"
    if "подум" in x or "think" in x:
        return "think"
    return "mixed"

# Step 5  Сложны,Средний,Простой 
def _normalize_complexity(raw: str) -> str:
    x = (raw or "").strip().lower()
    if "прост" in x or x == "simple":
        return "simple"
    if "слож" in x or x == "complex":
        return "complex"
    return "medium"

# Step 9 Возростные ограничения: 16+,18+,Без разницы
def _normalize_age_limit(raw: str) -> str:
    x = (raw or "").strip().lower()
    if "18" in x:
        return "18"
    if "16" in x:
        return "16"
    return "none"


def build_preferences_from_onboarding(user_id: int) -> Dict[str, Any]:
    """
    Собираем user_preferences из 10 шагов:
      q1..q9 из onboarding_answers + любимые тайтлы из onboarding_titles.
    """
    # q1
    q1 = get_onboarding_answer(user_id, "q1") or ""
    content_type = _normalize_content_type(q1)

    # q2 languages 
    q2_raw = get_onboarding_answer(user_id, "q2")
    languages: List[str] = []
    if q2_raw:
        payload = jload(q2_raw) or {}
        languages = payload.get("languages") or []
    # fallback: если вдруг было как обычная строка
    if isinstance(languages, str):
        languages = [languages]
    languages = [str(x).strip() for x in languages if str(x).strip()]

    # q3 audio
    q3 = get_onboarding_answer(user_id, "q3") or ""
    audio_pref = _normalize_audio_pref(q3)

    # q4 genres JSON
    q4_raw = get_onboarding_answer(user_id, "q4")
    liked_genres: List[str] = []
    if q4_raw:
        payload = jload(q4_raw) or {}
        liked_genres = payload.get("genres") or []
    if isinstance(liked_genres, str):
        liked_genres = [liked_genres]
    liked_genres = [str(x).strip() for x in liked_genres if str(x).strip()]

    # q5 avoid genres JSON
    q5_raw = get_onboarding_answer(user_id, "q5")
    blocked_genres: List[str] = []
    blocked_topics: List[str] = []
    if q5_raw:
        payload = jload(q5_raw) or {}
        blocked_genres = payload.get("avoid_genres") or []
        # если добавлял темы, можно их хранить в том же payload как avoid_topics
        blocked_topics = payload.get("avoid_topics") or []
    if isinstance(blocked_genres, str):
        blocked_genres = [blocked_genres]
    blocked_genres = [str(x).strip() for x in blocked_genres if str(x).strip()]

    if isinstance(blocked_topics, str):
        blocked_topics = [blocked_topics]
    blocked_topics = [str(x).strip() for x in blocked_topics if str(x).strip()]

    # q6 pace
    q6 = get_onboarding_answer(user_id, "q6") or ""
    pace = _normalize_pace(q6)

    # q7 mood
    q7 = get_onboarding_answer(user_id, "q7") or ""
    mood = _normalize_mood(q7)

    # q8 complexity
    q8 = get_onboarding_answer(user_id, "q8") or ""
    plot_complexity = _normalize_complexity(q8)

    # q9 age limit 
    q9_raw = get_onboarding_answer(user_id, "q9") or ""
 
    content_flags: List[str] = []
    if q9_raw.strip().startswith("{"):
        payload = jload(q9_raw) or {}
        age_limit = _normalize_age_limit(payload.get("age_limit") or "")
        content_flags = payload.get("flags") or []
    else:
        age_limit = _normalize_age_limit(q9_raw)

    if isinstance(content_flags, str):
        content_flags = [content_flags]
    content_flags = [str(x).strip() for x in content_flags if str(x).strip()]

    # step10 favorites
    liked_titles = get_onboarding_liked_titles(user_id)
    favorite_titles = [{"tmdb_id": int(x["tmdb_id"]), "media_type": x["media_type"]} for x in liked_titles]

    return {
        "user_id": user_id,
        "content_type": content_type,
        "languages": languages,
        "audio_pref": audio_pref,
        "liked_genres": liked_genres,
        "blocked_genres": blocked_genres,
        "blocked_topics": blocked_topics,
        "pace": pace,
        "mood": mood,
        "plot_complexity": plot_complexity,
        "age_limit": age_limit,
        "content_flags": content_flags,
        "favorite_titles": favorite_titles,
    }


def upsert_user_preferences(prefs: Dict[str, Any]) -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_preferences (
            user_id, content_type, languages_json, audio_pref,
            liked_genres_json, blocked_genres_json, blocked_topics_json,
            pace, mood, plot_complexity, age_limit, content_flags_json,
            favorite_titles_json, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            content_type=excluded.content_type,
            languages_json=excluded.languages_json,
            audio_pref=excluded.audio_pref,
            liked_genres_json=excluded.liked_genres_json,
            blocked_genres_json=excluded.blocked_genres_json,
            blocked_topics_json=excluded.blocked_topics_json,
            pace=excluded.pace,
            mood=excluded.mood,
            plot_complexity=excluded.plot_complexity,
            age_limit=excluded.age_limit,
            content_flags_json=excluded.content_flags_json,
            favorite_titles_json=excluded.favorite_titles_json,
            updated_at=CURRENT_TIMESTAMP
    """, (
        prefs["user_id"],
        prefs["content_type"],
        jdump(prefs["languages"]),
        prefs["audio_pref"],
        jdump(prefs["liked_genres"]),
        jdump(prefs["blocked_genres"]),
        jdump(prefs["blocked_topics"]),
        prefs["pace"],
        prefs["mood"],
        prefs["plot_complexity"],
        prefs["age_limit"],
        jdump(prefs["content_flags"]),
        jdump(prefs["favorite_titles"]),
    ))
    conn.commit()
    conn.close()


def get_user_preferences(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["languages"] = jload(d.pop("languages_json")) or []
    d["liked_genres"] = jload(d.pop("liked_genres_json")) or []
    d["blocked_genres"] = jload(d.pop("blocked_genres_json")) or []
    d["blocked_topics"] = jload(d.pop("blocked_topics_json")) or []
    d["content_flags"] = jload(d.pop("content_flags_json")) or []
    d["favorite_titles"] = jload(d.pop("favorite_titles_json")) or []
    return d


# TMDB genres + discover
_GENRE_CACHE: Dict[Tuple[str, str], Dict[str, int]] = {}  


def tmdb_get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not TMDB_API_KEY:
        raise RuntimeError("TMDB_API_KEY is not set")
    r = requests.get(f"{TMDB_BASE}{path}", params={**params, "api_key": TMDB_API_KEY}, timeout=10)
    r.raise_for_status()
    return r.json()


def get_genre_map(media_type: str, lang: str) -> Dict[str, int]:
    key = (media_type, lang)
    if key in _GENRE_CACHE:
        return _GENRE_CACHE[key]

    data = tmdb_get(f"/genre/{media_type}/list", {"language": lang})
    m: Dict[str, int] = {}
    for g in data.get("genres", []):
        name = (g.get("name") or "").strip().lower()
        gid = g.get("id")
        if name and isinstance(gid, int):
            m[name] = gid
    _GENRE_CACHE[key] = m
    return m


def names_to_genre_ids(media_type: str, lang: str, names: List[str]) -> List[int]:
    gm = get_genre_map(media_type, lang)
    out: List[int] = []
    for n in names:
        k = (n or "").strip().lower()
        if not k:
            continue
        gid = gm.get(k)
        if gid and gid not in out:
            out.append(gid)
    return out


def build_discover_params(media_type: str, prefs: Dict[str, Any], lang: str) -> Dict[str, Any]:
    liked_ids = names_to_genre_ids(media_type, lang, prefs.get("liked_genres", []))
    blocked_ids = names_to_genre_ids(media_type, lang, prefs.get("blocked_genres", []))

    p: Dict[str, Any] = {
        "language": lang,
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "vote_count.gte": 50,  
        "page": 1,
    }

    if liked_ids:
        p["with_genres"] = ",".join(map(str, liked_ids))
    if blocked_ids:
        p["without_genres"] = ",".join(map(str, blocked_ids))

    #  TMDB поддерживает только один original_language фильтром
    langs = prefs.get("languages") or []
    if langs:
        p["with_original_language"] = str(langs[0])
    if prefs.get("age_limit") == "18":
        p["include_adult"] = "true"   
    else:
        p["include_adult"] = "false"  

    return p


def normalize_tmdb_card(it: Dict[str, Any]) -> Dict[str, Any]:
    title = it.get("title") or it.get("name") or ""
    year = (it.get("release_date") or it.get("first_air_date") or "")[:4]
    poster_path = it.get("poster_path")
    media_type = it.get("media_type")

    return {
        "tmdb_id": it.get("id"),
        "media_type": media_type,
        "title": title,
        "year": year,
        "poster_url": (TMDB_IMG + poster_path) if poster_path else None,

        #  важно для формулы
        "genre_ids": it.get("genre_ids") or [],
        "original_language": it.get("original_language") or "",
        "vote_average": float(it.get("vote_average") or 0.0),
        "popularity": float(it.get("popularity") or 0.0),
        "overview": it.get("overview") or "",
    }



def get_cold_start_recommendations(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    prefs = get_user_preferences(user_id)
    if not prefs:
        return []

    lang = "ru-RU"  # язык ответа TMDB 

    # 1) Тип контента вопрос 1
    ct = prefs.get("content_type") or "both"
    types: List[str] = []
    if ct in ("movie", "both"):
        types.append("movie")
    if ct in ("tv", "both"):
        types.append("tv")

    # 2) Любимые/запрещенные жанры (вопросы 4 и 5)
    # переводим названия в ids отдельно под movie и tv
    liked_names = prefs.get("liked_genres") or []
    blocked_names = prefs.get("blocked_genres") or []

    liked_movie = set(names_to_genre_ids("movie", lang, liked_names))
    liked_tv = set(names_to_genre_ids("tv", lang, liked_names))
    blocked_movie = set(names_to_genre_ids("movie", lang, blocked_names))
    blocked_tv = set(names_to_genre_ids("tv", lang, blocked_names))

    # 3) Язык вопрос 2
    user_langs = set((prefs.get("languages") or [])) 

    # 4) Темп/настроение/сложность вопросы 6,7,8 
    signals = build_genre_sets_for_signals(lang)

    pace = prefs.get("pace") or "medium"                
    mood = prefs.get("mood") or "mixed"                 
    complexity = prefs.get("plot_complexity") or "medium"  

    # 5) Любимые тайтлы вопрос 10 используем recommendations 
    favorites = prefs.get("favorite_titles") or []

    # Собираем кандидатов 
    merged: Dict[Tuple[int, str], Dict[str, Any]] = {}
    sim_count: Dict[Tuple[int, str], int] = {}  

    #  фильтрация по жанрам,возрасту,языку
    for t in types:
        params = build_discover_params(t, prefs, lang)  
        data = tmdb_get(f"/discover/{t}", params)

        for it in data.get("results", []):
            card = normalize_tmdb_card(it)
            card["media_type"] = t
            key = (int(card["tmdb_id"]), t)
            merged[key] = card

    # Похожие на любимые 2-3 фаворита
    for fav in favorites[:3]:
        t = fav.get("media_type") or "movie"
        mid = int(fav.get("tmdb_id"))
        if t not in ("movie", "tv"):
            continue

        data = tmdb_get(f"/{t}/{mid}/recommendations", {"language": lang, "page": 1})
        for it in data.get("results", []):
            card = normalize_tmdb_card(it)
            card["media_type"] = t
            key = (int(card["tmdb_id"]), t)
            merged.setdefault(key, card)
            sim_count[key] = sim_count.get(key, 0) + 1

    # Скоринг: полноценная формула
    scored: List[Tuple[float, Dict[str, Any]]] = []

    for (tmdb_id, t), item in merged.items():
        genre_ids = [int(x) for x in (item.get("genre_ids") or []) if str(x).isdigit()]

        # Жёсткий safety: если вдруг без фильтра попал запрещенный жанр тогда выкидываем
        if t == "movie" and blocked_movie and (set(genre_ids) & blocked_movie):
            continue
        if t == "tv" and blocked_tv and (set(genre_ids) & blocked_tv):
            continue

        #  признаки 
        # жанры вопрос 4
        if t == "movie":
            G = jaccard(set(genre_ids), liked_movie)
        else:
            G = jaccard(set(genre_ids), liked_tv)

        # похожесть на любимые вопрос 10
        # чем чаще встретился среди рекомендаций любимых, тем выше шанс
        S = clamp01(sim_count.get((tmdb_id, t), 0) / 3.0)

        # язык вопрос 2
        orig_lang = (item.get("original_language") or "").strip()
        L = 1.0 if (orig_lang and orig_lang in user_langs) else 0.0

        # рейтинг 
        R = clamp01(float(item.get("vote_average") or 0.0) / 10.0)

        #  популярность нормируем логарифмом
        pop = float(item.get("popularity") or 0.0)
        P = clamp01(math.log1p(pop) / math.log1p(1000.0))

        #  темп вопрос 6 эвристика через жанры
        if pace == "fast":
            T = signal_score(genre_ids, signals["fast"])
        elif pace == "slow":
            T = signal_score(genre_ids, signals["slow"])
        else:
            T = 0.5  

        # настроение вопрос 7
        if mood == "light":
            M = signal_score(genre_ids, signals["light"])
        elif mood == "tense":
            M = signal_score(genre_ids, signals["tense"])
        elif mood == "inspiring":
            M = signal_score(genre_ids, signals["inspiring"])
        elif mood == "dark":
            M = signal_score(genre_ids, signals["dark"])
        elif mood == "think":
            M = signal_score(genre_ids, signals["think"])
        else:
            M = 0.5  # mixed

        # сложность сюжета вопрос 8
        if complexity == "simple":
            C = signal_score(genre_ids, signals["simple"])
        elif complexity == "complex":
            C = signal_score(genre_ids, signals["complex"])
        else:
            C = 0.5

        # Type: фильмы/сериалы (вопрос 1)
        if ct == "movie":
            Type = 1.0 if t == "movie" else 0.0
        elif ct == "tv":
            Type = 1.0 if t == "tv" else 0.0
        else:
            Type = 0.5  # both

        #  Итоговая формула кроме озвучки 
        score = (
            5.0 * G +
            6.0 * S +
            1.0 * L +
            2.0 * R +
            1.0 * P +
            0.7 * T +
            0.7 * M +
            0.7 * C +
            0.5 * Type
        )

        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:limit]]



# Pages 
@app.route("/")
def home():
    return render_template("index.html")


#  Аутентификация
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not nickname or not email or not password:
            flash("Fill all fields.")
            return redirect(url_for("signup"))

        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (nickname, email, password_hash) VALUES (?, ?, ?)",
                (nickname, email, generate_password_hash(password)),
            )
            conn.commit()
            user_id = cur.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            flash("Email already exists.")
            return redirect(url_for("signup"))

        conn.close()

        session["user_id"] = user_id
        session["nickname"] = nickname
        return redirect(url_for("onboarding_intro"))

    return render_template("signup.html")

# вход
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "").strip()

        if not login_value or not password:
            flash("Fill all fields.")
            return redirect(url_for("login"))

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE lower(email)=lower(?) OR nickname=?",
            (login_value, login_value),
        )
        user = cur.fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid nickname/email or password.")
            return redirect(url_for("login"))

        session["user_id"] = user["id"]
        session["nickname"] = user["nickname"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")

# выход из аккаунта
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


#  Главная страница
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = int(session["user_id"])
    prefs = get_user_preferences(user_id)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM watch_history WHERE user_id=? LIMIT 1", (user_id,))
    has_history = cur.fetchone() is not None
    conn.close()

    show_recommendations_block = bool(prefs) and (not has_history)
    show_continue_watching = has_history

    return render_template(
        "dashboard.html",
        nickname=session.get("nickname", "User"),
        show_recommendations_block=show_recommendations_block,
        show_continue_watching=show_continue_watching,
    )

@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = int(session["user_id"])

    if request.method == "POST":
        form_type = (request.form.get("form_type") or "").strip()

        conn = get_db()
        cur = conn.cursor()

        # взять текущего юзера
        user = cur.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            conn.close()
            session.clear()
            return redirect(url_for("login"))

        #  Update nickname
        if form_type == "nickname":
            nickname = (request.form.get("nickname") or "").strip()
            if len(nickname) < 2:
                flash("Nickname is too short.")
                conn.close()
                return redirect(url_for("settings_page"))

            cur.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, user_id))
            conn.commit()
            conn.close()

            session["nickname"] = nickname
            flash("Nickname updated.")
            return redirect(url_for("settings_page"))

        # Update email 
        if form_type == "email":
            email = (request.form.get("email") or "").strip().lower()
            password = (request.form.get("password") or "").strip()

            if not email or "@" not in email:
                flash("Invalid email.")
                conn.close()
                return redirect(url_for("settings_page"))

            if not check_password_hash(user["password_hash"], password):
                flash("Wrong password.")
                conn.close()
                return redirect(url_for("settings_page"))

            try:
                cur.execute("UPDATE users SET email=? WHERE id=?", (email, user_id))
                conn.commit()
            except sqlite3.IntegrityError:
                conn.close()
                flash("This email is already used.")
                return redirect(url_for("settings_page"))

            conn.close()
            flash("Email updated.")
            return redirect(url_for("settings_page"))

        #  Update password 
        if form_type == "password":
            old_password = (request.form.get("old_password") or "").strip()
            new_password = (request.form.get("new_password") or "").strip()
            new_password2 = (request.form.get("new_password2") or "").strip()

            if not check_password_hash(user["password_hash"], old_password):
                flash("Wrong current password.")
                conn.close()
                return redirect(url_for("settings_page"))

            if len(new_password) < 6:
                flash("New password must be at least 6 characters.")
                conn.close()
                return redirect(url_for("settings_page"))

            if new_password != new_password2:
                flash("Passwords do not match.")
                conn.close()
                return redirect(url_for("settings_page"))

            cur.execute(
                "UPDATE users SET password_hash=? WHERE id=?",
                (generate_password_hash(new_password), user_id),
            )
            conn.commit()
            conn.close()

            flash("Password updated.")
            return redirect(url_for("settings_page"))

        conn.close()
        flash("Unknown action.")
        return redirect(url_for("settings_page"))

    # GET
    conn = get_db()
    cur = conn.cursor()
    user = cur.execute("SELECT id, nickname, email FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()

    return render_template("settings.html", nickname=user["nickname"], email=user["email"])

@app.route("/movies")
def movies_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("movies.html", nickname=session.get("nickname", "User"))

# вопросы интро
@app.route("/onboarding")
def onboarding_intro():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("onboarding_intro.html")
@app.route("/onboarding/skip", methods=["POST"])
def onboarding_skip():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))
@app.route("/onboarding/start", methods=["POST"])
def onboarding_start():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("onboarding_step", step=1))


# Вопросы по этопно
@app.route("/onboarding/step/<int:step>", methods=["GET", "POST"])
def onboarding_step(step: int):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if step < 1:
        return redirect(url_for("onboarding_step", step=1))
    if step > 10:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        key = f"q{step}"
        answer_value = ""
        # Step 1 / 3 / 6 / 7 / 8 / 9 etc: обычной ответ текстом просто сохрянем как строку
        if "answer" in request.form:
            answer_value = request.form.get("answer", "").strip()

        # Step 2: languages может быть несколько ответов 
        elif "languages" in request.form:
            langs = request.form.getlist("languages")
            other_text = request.form.get("other_text", "").strip()
            payload = {"languages": langs}
            if "other" in langs and other_text:
                payload["other_text"] = other_text
            answer_value = json.dumps(payload, ensure_ascii=False)

        # Step 4: genres 3-5 
        elif "genres" in request.form:
            genres = request.form.getlist("genres")
            other_text = request.form.get("other_text", "").strip()

            if len(genres) < 3 or len(genres) > 5:
                flash("Please choose from 3 to 5 genres.")
                return redirect(url_for("onboarding_step", step=4))

            payload = {"genres": genres}
            if "other" in genres and other_text:
                payload["other_text"] = other_text
            answer_value = json.dumps(payload, ensure_ascii=False)

        # Step 5: avoid genres может быть несколько тем и жанров 
        elif "avoid_genres" in request.form:
            avoid = request.form.getlist("avoid_genres")
            other_text = request.form.get("other_text", "").strip()
            payload = {"avoid_genres": avoid}
            if "other" in avoid and other_text:
                payload["other_text"] = other_text
            if "avoid_topics" in request.form:
                payload["avoid_topics"] = request.form.getlist("avoid_topics")
            answer_value = json.dumps(payload, ensure_ascii=False)

        # Step 9 если ты добавишь flags, можешь отправлять JSON с флагами контента

        # Save answer для вопросов 
        if answer_value:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO onboarding_answers (user_id, question_key, answer)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, question_key) DO UPDATE SET answer=excluded.answer
            """, (session["user_id"], key, answer_value))
            conn.commit()
            conn.close()

        #  Step 10 любимые тайтлы сохраняются через отдельный API
        if step == 10:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) AS cnt
                FROM onboarding_titles
                WHERE user_id=? AND liked=1
            """, (session["user_id"],))
            liked_cnt = int(cur.fetchone()["cnt"])
            conn.close()

            if liked_cnt < 5:
                flash("Select at least 5 titles you liked.")
                return redirect(url_for("onboarding_step", step=10))

            #  Собираем preferences из ответов и сохраняем в user_preferences
            prefs = build_preferences_from_onboarding(int(session["user_id"]))
            upsert_user_preferences(prefs)

            return redirect(url_for("dashboard"))

        return redirect(url_for("onboarding_step", step=step + 1))

    # GET рендерим шаблон для текущего шага
    if step == 1:
        return render_template("onboarding_step_1.html")
    if step == 2:
        return render_template("onboarding_step_2.html")
    if step == 3:
        return render_template("onboarding_step_3.html")
    if step == 4:
        return render_template("onboarding_step_4.html")
    if step == 5:
        return render_template("onboarding_step_5.html")
    if step == 6:
        return render_template("onboarding_step_6.html")
    if step == 7:
        return render_template("onboarding_step_7.html")
    if step == 8:
        return render_template("onboarding_step_8.html")
    if step == 9:
        return render_template("onboarding_step_9.html")
    if step == 10:
        return render_template("onboarding_step_10.html")

    return render_template("onboarding_step_placeholder.html", step=step)


#  TMDB API backend proxy для пойска и деталей тайтлов
@app.get("/api/tmdb/search")
def api_tmdb_search():
    q = (request.args.get("q") or "").strip()
    lang = (request.args.get("lang") or "ru-RU").strip()
    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500
    if len(q) < 2:
        return jsonify({"results": []})

    r = requests.get(
        f"{TMDB_BASE}/search/multi",
        params={"api_key": TMDB_API_KEY, "query": q, "language": lang},
        timeout=10
    )
    r.raise_for_status()
    data = r.json()

    results = []
    for it in data.get("results", []):
        if it.get("media_type") not in ("movie", "tv"):
            continue
        title = it.get("title") or it.get("name") or ""
        year = (it.get("release_date") or it.get("first_air_date") or "")[:4]
        poster_path = it.get("poster_path")
        results.append({
            "tmdb_id": it.get("id"),
            "media_type": it.get("media_type"),
            "title": title,
            "year": year,
            "poster_url": (TMDB_IMG + poster_path) if poster_path else None
        })

    return jsonify({"results": results})

# TMDB детали по id для карточки в избранном и рекомендациях
@app.get("/api/tmdb/details/<int:tmdb_id>")
def api_tmdb_details(tmdb_id: int):
    lang = (request.args.get("lang") or "ru-RU").strip()
    media_type = (request.args.get("type") or "movie").strip()  # <-- ДОБАВИЛИ

    if media_type not in ("movie", "tv"):
        media_type = "movie"

    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    r = requests.get(
        f"{TMDB_BASE}/{media_type}/{tmdb_id}",
        params={"api_key": TMDB_API_KEY, "language": lang},
        timeout=10
    )

    # fallback (на всякий случай)
    if r.status_code == 404:
        other = "tv" if media_type == "movie" else "movie"
        r = requests.get(
            f"{TMDB_BASE}/{other}/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "language": lang},
            timeout=10
        )

    r.raise_for_status()
    it = r.json()

    poster_path = it.get("poster_path")
    return jsonify({
        "tmdb_id": tmdb_id,
        "title": it.get("title") or it.get("name"),
        "overview": it.get("overview"),
        "genres": [g["name"] for g in it.get("genres", [])],
        "poster_url": (TMDB_IMG + poster_path) if poster_path else None,
        "release_date": it.get("release_date") or it.get("first_air_date"),
        "media_type": media_type,
    })

# Save, Get onboarding titles
@app.post("/api/onboarding/title")
def save_onboarding_title():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True)
    try:
        tmdb_id = int(data.get("tmdb_id"))
    except Exception:
        return jsonify({"error": "tmdb_id is required"}), 400

    media_type = (data.get("media_type") or "movie").strip()
    title = (data.get("title") or "").strip()
    liked = 1 if data.get("liked") else 0

    if media_type not in ("movie", "tv"):
        media_type = "movie"
    if not title:
        title = f"tmdb:{tmdb_id}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO onboarding_titles (user_id, tmdb_id, media_type, title, liked)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, tmdb_id) DO UPDATE SET
            liked=excluded.liked,
            title=excluded.title,
            media_type=excluded.media_type
    """, (session["user_id"], tmdb_id, media_type, title, liked))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# Onboarding titles для отображения на стрранице онбординга и для передачи в формулу рекомендаций 
@app.get("/api/onboarding/titles")
def get_onboarding_titles():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT tmdb_id, media_type, title, liked, created_at
        FROM onboarding_titles
        WHERE user_id=?
        ORDER BY created_at DESC
    """, (session["user_id"],))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"items": rows})

# onboarding titles удаление если юзер предложил тайтл по ошибке или передумал 
@app.delete("/api/onboarding/title/<int:tmdb_id>")
def delete_onboarding_title(tmdb_id: int):
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM onboarding_titles WHERE user_id=? AND tmdb_id=?",
                (session["user_id"], tmdb_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# Recommendations API для нового пользователя на основе его предпочтений из онбординга 
@app.get("/api/recommendations")
def api_recommendations():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    limit = int(request.args.get("limit") or 20)
    limit = max(1, min(limit, 60))

    only_type = (request.args.get("type") or "").strip()  

    items = get_cold_start_recommendations(int(session["user_id"]), limit=limit*2)

    if only_type in ("movie", "tv"):
        items = [x for x in items if (x.get("media_type") == only_type)]

    return jsonify({"items": items[:limit]})


# trending и релизы для отображения на главной странице
@app.get("/api/trending")
def api_trending():
    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    lang = (request.args.get("lang") or "ru-RU").strip()
    limit = int(request.args.get("limit") or 20)
    limit = max(1, min(limit, 40))
    data = tmdb_get("/trending/all/week", {"language": lang, "page": 1})
    items = []
    for it in data.get("results", []):
        if it.get("media_type") not in ("movie", "tv"):
            continue
        card = normalize_tmdb_card(it)
        card["media_type"] = it.get("media_type")
        items.append(card)
        if len(items) >= limit:
            break
    return jsonify({"items": items})

# releases для отображения на главной странице что сейчас идет в кино и новые сериалы
@app.get("/api/releases")
def api_releases():
    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    lang = (request.args.get("lang") or "ru-RU").strip()
    kind = (request.args.get("kind") or "movie").strip()  # movie | tv
    limit = int(request.args.get("limit") or 10)
    limit = max(1, min(limit, 20))

    if kind == "tv":
        data = tmdb_get("/tv/on_the_air", {"language": lang, "page": 1})
        media_type = "tv"
    else:
        data = tmdb_get("/movie/now_playing", {"language": lang, "page": 1})
        media_type = "movie"

    items = []
    for it in data.get("results", []):
        tmdb_id = it.get("id")
        title = it.get("title") or it.get("name") or ""
        date = it.get("release_date") or it.get("first_air_date") or ""
        year = date[:4]
        overview = it.get("overview") or ""

        backdrop = it.get("backdrop_path")
        poster = it.get("poster_path")

        img_path = backdrop or poster

        items.append({
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "title": title,
            "year": year,
            "release_date": date,
            "overview": overview,
            "img_url": (TMDB_IMG + img_path) if img_path else None,
            "poster_url": (TMDB_IMG + poster) if poster else None,
        })
        if len(items) >= limit:
            break
    return jsonify({"items": items})

# трейлер для карточки и страницы просмотров 
@app.get("/api/tmdb/trailer/<int:tmdb_id>")
def api_tmdb_trailer(tmdb_id: int):
    lang = (request.args.get("lang") or "ru-RU").strip()
    media_type = (request.args.get("type") or "movie").strip()

    if media_type not in ("movie", "tv"):
        media_type = "movie"

    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    r = requests.get(
        f"{TMDB_BASE}/{media_type}/{tmdb_id}/videos",
        params={"api_key": TMDB_API_KEY, "language": lang},
        timeout=10
    )

    # fallback (на всякий)
    if r.status_code == 404:
        other = "tv" if media_type == "movie" else "movie"
        r = requests.get(
            f"{TMDB_BASE}/{other}/{tmdb_id}/videos",
            params={"api_key": TMDB_API_KEY, "language": lang},
            timeout=10
        )

    r.raise_for_status()
    data = r.json()

    for v in data.get("results", []):
        if v.get("site") == "YouTube" and v.get("type") in ("Trailer", "Teaser"):
            return jsonify({"key": v.get("key"), "name": v.get("name"), "type": v.get("type")})

    return jsonify({"error": "no trailer"}), 404


# watch страница для отображения плеера и сохранения прогресса просмотра 
@app.get("/watch/<media_type>/<int:tmdb_id>")
def watch_page(media_type: str, tmdb_id: int):
    if "user_id" not in session:
        return redirect(url_for("login"))
    if media_type not in ("movie", "tv"):
        media_type = "movie"
    return render_template("watch.html", media_type=media_type, tmdb_id=tmdb_id)

# старт просмотра и сохранение в истории просмотров
@app.post("/api/watch/start")
def api_watch_start():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    tmdb_id = int(data.get("tmdb_id") or 0)
    media_type = (data.get("media_type") or "movie").strip()
    title = (data.get("title") or "").strip()
    poster_url = data.get("poster_url")

    if tmdb_id <= 0:
        return jsonify({"error": "tmdb_id required"}), 400
    if media_type not in ("movie", "tv"):
        media_type = "movie"
    if not title:
        title = f"tmdb:{tmdb_id}"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO watch_history (user_id, tmdb_id, media_type, title, poster_url, progress)
        VALUES (?, ?, ?, ?, ?, 0)
        ON CONFLICT(user_id, tmdb_id, media_type) DO UPDATE SET
            title=excluded.title,
            poster_url=COALESCE(excluded.poster_url, watch_history.poster_url),
            last_watched_at=CURRENT_TIMESTAMP
    """, (session["user_id"], tmdb_id, media_type, title, poster_url))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})

# прогресс просмотра сохраняем в истории просмотров и для формулы рекомендацй
@app.post("/api/watch/progress")
def api_watch_progress():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    tmdb_id = int(data.get("tmdb_id") or 0)
    media_type = (data.get("media_type") or "movie").strip()
    progress = int(data.get("progress") or 0)

    if tmdb_id <= 0:
        return jsonify({"error": "tmdb_id required"}), 400
    if media_type not in ("movie", "tv"):
        media_type = "movie"

    # clamp 0..100
    if progress < 0: progress = 0
    if progress > 100: progress = 100

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE watch_history
        SET progress=?, last_watched_at=CURRENT_TIMESTAMP
        WHERE user_id=? AND tmdb_id=? AND media_type=?
    """, (progress, session["user_id"], tmdb_id, media_type))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "progress": progress})

# continue watching для отображения на главной странице и быстрого доступа к просмотру 
@app.get("/api/continue_watching")
def api_continue_watching():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    limit = int(request.args.get("limit") or 12)
    if limit < 1: limit = 1
    if limit > 30: limit = 30

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT tmdb_id, media_type, title, poster_url, progress, last_watched_at
        FROM watch_history
        WHERE user_id=? AND progress < 100
        ORDER BY last_watched_at DESC
        LIMIT ?
    """, (session["user_id"], limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"items": rows})

# статус просмотров для отображения на карточках рекомендаций и избронного, чтобы показать прогресс и кнопку продолжить если юзер уже начал смотреть этот тайтл ранее
@app.get("/api/watch/status/<media_type>/<int:tmdb_id>")
def api_watch_status(media_type: str, tmdb_id: int):
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    if media_type not in ("movie", "tv"):
        media_type = "movie"

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("""
        SELECT progress, title, poster_url
        FROM watch_history
        WHERE user_id=? AND tmdb_id=? AND media_type=?
    """, (session["user_id"], tmdb_id, media_type)).fetchone()
    conn.close()

    if not row:
        return jsonify({"exists": False, "progress": 0})
    return jsonify({"exists": True, "progress": int(row["progress"] or 0)})

# movie genres для фильтрации и отображения жанров в вопросах онбординга и на страницк вопросов 
@app.get("/api/genres/movie")
def api_movie_genres():
    lang = (request.args.get("lang") or "ru-RU").strip()
    data = tmdb_get("/genre/movie/list", {"language": lang})
    items = [{"id": g["id"], "name": g["name"]} for g in data.get("genres", [])]
    return jsonify({"items": items})


# movies discover для отображения фильмов по фильтрам жанров,года,регионы 
@app.get("/api/movies/discover")
def api_movies_discover():
    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    lang = (request.args.get("lang") or "ru-RU").strip()
    page = max(1, min(int(request.args.get("page") or 1), 20))

    genres = (request.args.get("genres") or "").strip()   # "28,12"
    year = (request.args.get("year") or "").strip()       # "2024"
    region = (request.args.get("region") or "").strip()   # "US"
    sort = (request.args.get("sort") or "popularity.desc").strip()

    allowed_sorts = {
        "popularity.desc", "popularity.asc",
        "release_date.desc", "release_date.asc",
        "vote_average.desc", "vote_average.asc",
        "vote_count.desc", "vote_count.asc",
        "revenue.desc", "revenue.asc",
    }
    if sort not in allowed_sorts:
        sort = "popularity.desc"

    params = {
        "language": lang,
        "page": page,
        "sort_by": sort,
        "include_adult": "false",
        "vote_count.gte": 50,
    }

    if genres:
        params["with_genres"] = genres
    if year.isdigit():
        params["primary_release_year"] = year
    if region:
        params["region"] = region

    data = tmdb_get("/discover/movie", params)

    items = []
    for it in data.get("results", []):
        card = normalize_tmdb_card(it)
        card["media_type"] = "movie"
        items.append(card)

    return jsonify({
        "items": items,
        "page": data.get("page", page),
        "total_pages": data.get("total_pages", 1),
    })


# movies top для отображения топ фильмов по рейтингу на главной странице
@app.get("/api/movies/top")
def api_movies_top():
    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    lang = (request.args.get("lang") or "ru-RU").strip()
    kind = (request.args.get("kind") or "top30").strip()
    limit = 30 if kind == "top30" else 60

    endpoint = "/movie/top_rated"  # <-- вместо popular

    items = []
    page = 1
    while len(items) < limit and page <= 5:
        data = tmdb_get(endpoint, {"language": lang, "page": page})
        for it in data.get("results", []):
            card = normalize_tmdb_card(it)
            card["media_type"] = "movie"
            items.append(card)
            if len(items) >= limit:
                break
        page += 1

    return jsonify({"items": items[:limit]})

# series genres для филтраций жанров  по вопросам
@app.route("/series")
def series_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("series.html", nickname=session.get("nickname", "User"))

# genres tv для отображения жанров сериалов в вопросах
@app.get("/api/genres/tv")
def api_tv_genres():
    lang = (request.args.get("lang") or "ru-RU").strip()
    data = tmdb_get("/genre/tv/list", {"language": lang})
    items = [{"id": g["id"], "name": g["name"]} for g in data.get("genres", [])]
    return jsonify({"items": items})

# descover tv для отображения по фильртрам 
@app.get("/api/tv/discover")
def api_tv_discover():
    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    lang = (request.args.get("lang") or "ru-RU").strip()
    page = max(1, min(int(request.args.get("page") or 1), 20))

    genres = (request.args.get("genres") or "").strip()   
    year = (request.args.get("year") or "").strip()       
    region = (request.args.get("region") or "").strip()   

    params = {
        "language": lang,
        "page": page,
        "sort_by": "popularity.desc",
        "include_adult": "false",
        "vote_count.gte": 50,
    }

    if genres:
        params["with_genres"] = genres
    if year.isdigit():
        # для TV это first_air_date_year
        params["first_air_date_year"] = year

    data = tmdb_get("/discover/tv", params)

    items = []
    for it in data.get("results", []):
        card = normalize_tmdb_card(it)
        card["media_type"] = "tv"
        items.append(card)

    return jsonify({
        "items": items,
        "page": data.get("page", page),
        "total_pages": data.get("total_pages", 1),
    })

# top tv для отображения топ сериалов по рейтингу 
@app.get("/api/tv/top")
def api_tv_top():
    if not TMDB_API_KEY:
        return jsonify({"error": "TMDB_API_KEY is not set"}), 500

    lang = (request.args.get("lang") or "ru-RU").strip()
    kind = (request.args.get("kind") or "top30").strip()
    limit = 30 if kind == "top30" else 60

    endpoint = "/tv/top_rated"
    items = []
    page = 1
    while len(items) < limit and page <= 5:
        data = tmdb_get(endpoint, {"language": lang, "page": page})
        for it in data.get("results", []):
            card = normalize_tmdb_card(it)
            card["media_type"] = "tv"
            items.append(card)
            if len(items) >= limit:
                break
        page += 1

    return jsonify({"items": items[:limit]})

# my_list страница для отображения сохраненных фильмов и сериалов
@app.route("/my-list")
def my_list_page():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("my_list.html", nickname=session.get("nickname", "User"))

# my_list API для получения списка сохраненных фил/сер
@app.get("/api/my_list")
def api_my_list():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    limit = int(request.args.get("limit") or 40)
    limit = max(1, min(limit, 200))

    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT tmdb_id, media_type, title, poster_url, created_at
        FROM watchlist
        WHERE user_id=?
        ORDER BY created_at DESC
        LIMIT ?
    """, (session["user_id"], limit)).fetchall()
    conn.close()

    return jsonify({"items": [dict(r) for r in rows]})

# my_list API для отображения кнопки адд 
@app.post("/api/my_list/add")
def api_my_list_add():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    tmdb_id = int(data.get("tmdb_id") or 0)
    media_type = (data.get("media_type") or "movie").strip()
    title = (data.get("title") or "").strip()
    poster_url = data.get("poster_url")

    if tmdb_id <= 0:
        return jsonify({"error": "tmdb_id required"}), 400
    if media_type not in ("movie", "tv"):
        media_type = "movie"
    if not title:
        title = f"tmdb:{tmdb_id}"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO watchlist (user_id, tmdb_id, media_type, title, poster_url)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, tmdb_id, media_type) DO UPDATE SET
            title=excluded.title,
            poster_url=COALESCE(excluded.poster_url, watchlist.poster_url),
            created_at=CURRENT_TIMESTAMP
    """, (session["user_id"], tmdb_id, media_type, title, poster_url))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})

# my_list API для отображения кнопки ремув
@app.post("/api/my_list/remove")
def api_my_list_remove():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(force=True) or {}
    tmdb_id = int(data.get("tmdb_id") or 0)
    media_type = (data.get("media_type") or "movie").strip()
    if tmdb_id <= 0:
        return jsonify({"error": "tmdb_id required"}), 400
    if media_type not in ("movie", "tv"):
        media_type = "movie"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM watchlist WHERE user_id=? AND tmdb_id=? AND media_type=?",
                (session["user_id"], tmdb_id, media_type))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})



if __name__ == "__main__":
    app.run(debug=True)
