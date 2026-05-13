from __future__ import annotations

import json
import os
import re
import time
from html import unescape
from html.parser import HTMLParser
from threading import Lock
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, Response


GIRO_BASE = os.getenv("GIRO_BASE", "https://www.giroditalia.it/en").rstrip("/")
FETCH_TIMEOUT_SEC = float(os.getenv("GIRO_FETCH_TIMEOUT_SEC", "12"))
CACHE_TTL_SEC = int(os.getenv("GIRO_CACHE_TTL_SEC", "45"))
USER_AGENT = os.getenv(
    "GIRO_USER_AGENT",
    "Grafana Giro Race Control/1.0 (+https://www.giroditalia.it)",
)

CLASSIFICATION_CODES = {
    "gc": ("CLGEN", "General classification"),
    "points": ("CLPUNGEN", "Points classification"),
    "mountains": ("CLGPMGEN", "Mountains classification"),
    "youth": ("CLGENGIO", "Youth classification"),
    "team": ("CLSQAGEN", "Super Team classification"),
}

TEAM_ALIASES = {
    "NCI": ["NCI", "NETCOMPANY INEOS", "INEOS", "INEOS GRENADIERS"],
}

app = FastAPI(title="Giro d'Italia Race Control Data", version="1.0.0")

_cache: dict[str, tuple[float, Any]] = {}
_source_status: dict[str, dict[str, Any]] = {}
_lock = Lock()


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return " ".join(self.parts)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _cache_get(key: str) -> Any | None:
    with _lock:
        item = _cache.get(key)
        if not item:
            return None
        ts, value = item
        if time.time() - ts > CACHE_TTL_SEC:
            return None
        return value


def _cache_set(key: str, value: Any) -> Any:
    with _lock:
        _cache[key] = (time.time(), value)
    return value


def _record_source(name: str, url: str, ok: bool, error: str | None = None) -> None:
    _source_status[name] = {
        "source": name,
        "url": url,
        "ok": ok,
        "error": error or "",
        "checked_at_ms": _now_ms(),
    }


def _fetch_text(url: str, source_name: str) -> str:
    key = f"text:{url}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urlopen(req, timeout=FETCH_TIMEOUT_SEC) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="replace")
            _record_source(source_name, url, True)
            return _cache_set(key, text)
    except (OSError, URLError) as exc:
        _record_source(source_name, url, False, str(exc))
        stale = _cache.get(key)
        if stale:
            return stale[1]
        raise


def _fetch_json(url: str, source_name: str) -> Any:
    text = _fetch_text(url, source_name)
    return json.loads(text)


def _strip_html(value: Any) -> str:
    if value is False or value is None:
        return ""
    text = str(value)
    parser = _TextExtractor()
    parser.feed(text)
    cleaned = parser.text() or re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(cleaned)).strip()


def _num(value: Any) -> float | None:
    if value is None or value is False:
        return None
    text = str(value).strip().replace(",", ".")
    text = text.replace("−", "-")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def _int(value: Any) -> int:
    parsed = _num(value)
    return int(parsed) if parsed is not None else 0


def _human_group(value: Any) -> str:
    mapping = {
        "GRUPPO_TESTA": "Front group",
        "GRUPPO_INSEGUITORI": "Chasers",
        "GRUPPO_MAGLIA_ROSA": "Maglia Rosa group",
        "GRUPPO_PRINCIPALE": "Main group",
    }
    if value in mapping:
        return mapping[value]
    text = str(value or "").replace("GRUPPO_", "").replace("_", " ").strip()
    return text.title() if text else "Group"


def _rider_name(rider: dict[str, Any]) -> str:
    return " ".join([str(rider.get("nome") or "").strip(), str(rider.get("cognome") or "").strip()]).strip()


def _livefeed(stage: int) -> dict[str, Any]:
    return _fetch_json(f"{GIRO_BASE}/livefeed/tappa/{stage}/", "official_livefeed")


def _headlines() -> dict[str, Any]:
    return _fetch_json(f"{GIRO_BASE}/headlines/", "official_headlines")


def _groups(feed: dict[str, Any]) -> list[dict[str, Any]]:
    return feed.get("timeline", {}).get("linea", {}).get("gruppi", []) or []


def _watched_codes(team: str) -> set[str]:
    raw = (team or "NCI").split(" ")[0].upper()
    return {alias.upper() for alias in TEAM_ALIASES.get(raw, [raw])}


def _race_now_payload(stage: int) -> dict[str, Any]:
    feed = _livefeed(stage)
    timeline = feed.get("timeline", {})
    stage_data = timeline.get("dati_tappa", {})
    tech = timeline.get("dati_tecnici", {})
    box = timeline.get("linea", {}).get("box_testa_corsa", {})
    groups = _groups(feed)

    total_km = _num(tech.get("lunghezza_km"))
    done_km = _num(tech.get("percorsi"))
    km_to_go = _num(box.get("distanza_arrivo"))
    if km_to_go is not None:
        km_to_go = max(0.0, abs(km_to_go))
    progress_pct = None
    if total_km and done_km is not None:
        progress_pct = max(0.0, min(100.0, round(done_km / total_km * 100, 1)))

    front = groups[0] if groups else {}
    front_riders = front.get("corridori", []) or []
    front_names = [_rider_name(r) for r in front_riders if _rider_name(r)]
    front_summary = ", ".join(front_names[:3])
    if len(front_names) > 3:
        front_summary += f" +{len(front_names) - 3}"

    elapsed = stage_data.get("tempo_trascorso") or ""
    finished = bool(total_km and done_km is not None and done_km >= total_km and (km_to_go or 0) <= 0.1)
    if finished:
        race_state = "finished"
        state_label = "Finished"
    elif elapsed or groups:
        race_state = "live"
        state_label = "Live"
    else:
        race_state = "pre_race"
        state_label = "Pre-race"

    return {
        "stage": stage,
        "stage_no": stage_data.get("numero") or f"{stage:02d}",
        "route": stage_data.get("nome") or "",
        "date": stage_data.get("data") or "",
        "profile": stage_data.get("caratteristiche") or "",
        "elapsed": elapsed,
        "elapsed_minutes": _elapsed_minutes(elapsed),
        "avg_speed": stage_data.get("velocita_media") or "",
        "avg_speed_kmh": _num(stage_data.get("velocita_media")),
        "done_km": done_km,
        "total_km": total_km,
        "km_to_go": km_to_go,
        "progress_pct": progress_pct,
        "front_group_type": _human_group(front.get("tipo")),
        "front_group_size": len(front_riders),
        "front_summary": front_summary,
        "feed_refresh_sec": round(_int(feed.get("header", {}).get("time_refresh")) / 1000, 0),
        "last_update_ms": feed.get("header", {}).get("timestamp"),
        "expiration_ms": feed.get("header", {}).get("expiration_timestamp"),
        "race_state": race_state,
        "state_label": state_label,
        "official_livefeed_url": f"{GIRO_BASE}/livefeed/tappa/{stage}/",
    }


def _elapsed_minutes(value: str) -> float | None:
    if not value:
        return None
    h = re.search(r"(\d+)\s*h", value)
    m = re.search(r"(\d+)\s*'", value)
    total = 0
    if h:
        total += int(h.group(1)) * 60
    if m:
        total += int(m.group(1))
    return float(total) if total else None


def _classification_html() -> str:
    return _fetch_text(f"{GIRO_BASE}/classifiche/", "official_classifications")


def _tab_html(html: str, code: str) -> str:
    marker = f"js-tab-classifica-{code}"
    start = html.find(marker)
    if start < 0:
        return ""
    next_match = re.search(r'<div class="single-tab js-tab-classifica-', html[start + len(marker) :])
    end = start + len(marker) + next_match.start() if next_match else len(html)
    return html[start:end]


def _tag_text(block: str, class_name: str) -> str:
    match = re.search(rf'<div class="{re.escape(class_name)}[^"]*">(.*?)</div>', block, re.S)
    if not match:
        return ""
    return _strip_html(match.group(1))


def _parse_classification(kind: str) -> list[dict[str, Any]]:
    code, label = CLASSIFICATION_CODES[kind]
    html = _classification_html()
    tab = _tab_html(html, code)
    if not tab:
        _record_source("official_classifications", f"{GIRO_BASE}/classifiche/?classifica={code}", False, f"Missing tab {code}")
        return []

    rows: list[dict[str, Any]] = []
    for index, block in enumerate(re.findall(r'<div class="line-table">(.*?)(?=<div class="line-table">|</div>\s*</div>\s*</div>|$)', tab, re.S), start=1):
        team = _tag_text(block, "team p-3")
        time_value = _tag_text(block, "tempo p-3 is-text-right")
        gap = _tag_text(block, "distacco p-3 is-text-right")
        points = _tag_text(block, "punti p-3 is-text-right") or _tag_text(block, "tempo p-3 is-text-right")

        if kind == "team":
            name = team
            if not name:
                continue
            rows.append(
                {
                    "rank": index,
                    "team": name,
                    "value": time_value,
                    "time": time_value,
                    "gap": gap,
                    "classification": label,
                    "source": "Official Giro classifications",
                    "source_url": f"{GIRO_BASE}/classifiche/?classifica={code}",
                }
            )
            continue

        position_text = _tag_text(block, "position is-pink")
        first = _tag_text(block, "name p-3")
        surname = _tag_text(block, "surname p-3 is-bold")
        rider = " ".join([first, surname]).strip()
        if not rider:
            continue
        value = time_value if kind in {"gc", "youth"} else points
        rows.append(
            {
                "rank": _int(position_text) or index,
                "rider": rider,
                "team": team,
                "value": value,
                "time": time_value if kind in {"gc", "youth"} else "",
                "points": points if kind not in {"gc", "youth"} else "",
                "gap": gap,
                "classification": label,
                "source": "Official Giro classifications",
                "source_url": f"{GIRO_BASE}/classifiche/?classifica={code}",
            }
        )
    return rows


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "giro-data", "time_ms": _now_ms()}


@app.get("/api/v1/stage/{stage}/race-now")
def race_now(stage: int) -> dict[str, Any]:
    return _race_now_payload(stage)


@app.get("/api/v1/stage/{stage}/front-groups")
def front_groups(stage: int) -> list[dict[str, Any]]:
    feed = _livefeed(stage)
    rows = []
    for index, group in enumerate(_groups(feed), start=1):
        riders = group.get("corridori", []) or []
        rows.append(
            {
                "order": index,
                "group_type": _human_group(group.get("tipo")),
                "km": _num(group.get("km")),
                "gap": group.get("distacco") or "0:00",
                "rider_count": len(riders),
                "riders": ", ".join([_rider_name(r) for r in riders[:4] if _rider_name(r)]),
            }
        )
    return rows


@app.get("/api/v1/stage/{stage}/front-riders")
def front_riders(stage: int) -> list[dict[str, Any]]:
    feed = _livefeed(stage)
    rows = []
    for index, group in enumerate(_groups(feed), start=1):
        for rider in group.get("corridori", []) or []:
            rows.append(
                {
                    "group_order": index,
                    "group_type": _human_group(group.get("tipo")),
                    "gap": group.get("distacco") or "0:00",
                    "rider": _rider_name(rider),
                    "team_code": rider.get("team") or "",
                    "is_front": index == 1,
                    "km": _num(group.get("km")),
                }
            )
    return rows


@app.get("/api/v1/stage/{stage}/updates")
def updates(stage: int, limit: int = 5, q: str = "") -> list[dict[str, Any]]:
    data = _headlines()
    items: list[dict[str, Any]] = []
    breaking = data.get("breaking")
    if breaking:
        items.append(_update_row(breaking, True))
    for row in data.get("news", []) or []:
        items.append(_update_row(row, bool(row.get("breaking"))))

    if q:
        needle = q.lower()
        items = [row for row in items if needle in f"{row['title']} {row['summary']}".lower()]
    return items[: max(1, min(limit, 25))]


def _update_row(row: dict[str, Any], breaking: bool) -> dict[str, Any]:
    return {
        "time": row.get("time") or "",
        "breaking": bool(breaking),
        "title": _strip_html(row.get("title")),
        "summary": _strip_html(row.get("abstract")),
        "link": row.get("link") or "",
        "source": "Official Giro headlines",
    }


@app.get("/api/v1/stage/{stage}/ineos")
def ineos(stage: int, team: str = "NCI", view: str = "metrics") -> Any:
    raw_team_code = (team or "NCI").split(" ")[0].upper()
    codes = _watched_codes(team)
    riders = [row for row in front_riders(stage) if row["team_code"].upper() in codes]
    front = [row for row in riders if row["is_front"]]
    mentions = updates(stage, limit=10, q="ineos") + updates(stage, limit=10, q="netcompany")
    gc = _parse_classification("gc")
    gc_rows = [row for row in gc if any(alias in row.get("team", "").upper() for alias in codes)]
    top20 = [row for row in gc_rows if row.get("rank", 999) <= 20]

    if view == "riders":
        return riders
    if view == "front":
        return front
    if view == "mentions":
        return mentions[:10]
    if view == "gc":
        return gc_rows[:20]
    return [
        {"metric": "Live riders visible", "value": len(riders), "source": "Official livefeed"},
        {"metric": "Riders in front group", "value": len(front), "source": "Official livefeed"},
        {"metric": "Official update mentions", "value": len(mentions), "source": "Official headlines"},
        {
            "metric": "GC top 20 riders",
            "value": len(top20),
            "source": "Official classifications",
        },
        {
            "metric": "Watched team code",
            "value": raw_team_code,
            "source": "Dashboard variable",
        },
    ]


@app.get("/api/v1/standings/{kind}")
def standings(kind: str, limit: int = 5) -> list[dict[str, Any]]:
    if kind not in CLASSIFICATION_CODES:
        return [
            {
                "rank": 0,
                "classification": kind,
                "status": "unavailable",
                "message": f"Unknown classification '{kind}'",
                "source": "giro-data",
            }
        ]
    rows = _parse_classification(kind)
    if not rows:
        code, label = CLASSIFICATION_CODES[kind]
        return [
            {
                "rank": 0,
                "classification": label,
                "status": "unavailable",
                "message": "Official classification tab was not parsed",
                "source": "Official Giro classifications",
                "source_url": f"{GIRO_BASE}/classifiche/?classifica={code}",
            }
        ]
    return rows[: max(1, min(limit, 50))]


@app.get("/api/v1/stage/{stage}/weather")
def weather(stage: int) -> list[dict[str, Any]]:
    feed = _livefeed(stage)
    return [
        {
            "km": _num(row.get("km")),
            "location": row.get("location_name") or "",
            "description": row.get("desc") or "",
            "temperature": row.get("temp") or "",
            "wind": row.get("wind") or "",
        }
        for row in feed.get("timeline", {}).get("meteo", []) or []
    ]


@app.get("/api/v1/sources")
def sources() -> list[dict[str, Any]]:
    expected = [
        ("official_livefeed", f"{GIRO_BASE}/livefeed/tappa/${{stage}}/"),
        ("official_headlines", f"{GIRO_BASE}/headlines/"),
        ("official_classifications", f"{GIRO_BASE}/classifiche/"),
        ("giro_data_service", "http://giro-data:8080"),
    ]
    rows = []
    for name, url in expected:
        status = _source_status.get(name, {})
        rows.append(
            {
                "source": name,
                "url": status.get("url", url),
                "ok": status.get("ok", name == "giro_data_service"),
                "error": status.get("error", ""),
                "checked_at_ms": status.get("checked_at_ms", ""),
            }
        )
    return rows


@app.get("/api/v1/stage/{stage}/visuals")
def visuals(stage: int) -> dict[str, Any]:
    now = _race_now_payload(stage)
    return {
        "stage": stage,
        "hero_svg": "/assets/giro-control-room.svg",
        "route": now.get("route"),
        "profile": now.get("profile"),
        "official_route_url": f"{GIRO_BASE}/the-route/",
        "note": "Generated visual is decorative. Official endpoints remain the source of truth.",
    }


@app.get("/assets/giro-control-room.svg")
def giro_control_room_svg() -> Response:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
      <stop stop-color="#1b1f2a" offset="0"/>
      <stop stop-color="#3d1026" offset="0.55"/>
      <stop stop-color="#0f1720" offset="1"/>
    </linearGradient>
    <linearGradient id="pink" x1="0" x2="1">
      <stop stop-color="#ff4fa3" offset="0"/>
      <stop stop-color="#f3b13b" offset="1"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)"/>
  <path d="M60 520 C180 460 250 560 360 470 C475 375 560 420 660 330 C785 218 890 360 1020 230 C1090 165 1160 178 1220 130" fill="none" stroke="url(#pink)" stroke-width="18" stroke-linecap="round" opacity="0.95"/>
  <path d="M90 590 C210 530 315 615 430 520 C560 410 650 475 775 365 C900 255 1000 390 1190 250" fill="none" stroke="#ffffff" stroke-width="4" opacity="0.6"/>
  <g opacity="0.26" stroke="#fff" stroke-width="1">
    <path d="M0 600H1280M0 480H1280M0 360H1280M0 240H1280M0 120H1280"/>
    <path d="M160 0V720M320 0V720M480 0V720M640 0V720M800 0V720M960 0V720M1120 0V720"/>
  </g>
  <g transform="translate(835 410)" fill="none" stroke="#fff" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="0" cy="105" r="58" stroke-width="12" opacity="0.86"/>
    <circle cx="235" cy="105" r="58" stroke-width="12" opacity="0.86"/>
    <path d="M0 105 L78 18 L142 105 L235 105 L168 0 L78 18" stroke-width="12"/>
    <circle cx="150" cy="-50" r="24" fill="#fff" stroke="none"/>
    <path d="M137 -28 L94 20 L155 40 L198 92" stroke-width="14"/>
    <path d="M94 20 L55 90" stroke-width="14"/>
  </g>
  <g font-family="Inter,Arial,sans-serif">
    <text x="60" y="105" fill="#fff" font-size="54" font-weight="800">GIRO RACE CONTROL</text>
    <text x="62" y="152" fill="#ffd3e9" font-size="24">Live route, front group, updates and INEOS watch</text>
    <text x="62" y="652" fill="#ffffff" opacity="0.72" font-size="18">Decorative generated visual. Race data comes from official Giro endpoints.</text>
  </g>
</svg>"""
    return Response(content=svg, media_type="image/svg+xml")
