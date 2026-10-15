import json
import logging
import re
import hashlib
import tempfile
from dataclasses import dataclass
from cache_tools import TTLCache, singleflight
import mimetypes
import os
import ssl
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse, parse_qs, unquote
import urllib.request
from rooms import build_rooms_index
from teachers import teachers_from_groups, departments_from_teachers, combine_teacher_catalog
from catalog import stamp_schedule, source_metadata

from parser import (
    ESSTU_BASE_URL,
    SECTIONS,
    get_week_num,
    normalize_group_name,
    parse_groups_list_html,
    parse_group_schedule_html,
    parse_departments_list_html,
    parse_department_teachers_html,
    merge_teacher_schedules,
    normalize_teacher_key,
)

LOGGER = logging.getLogger(__name__)
CACHE = TTLCache()
CACHE_TTL_SECONDS = 900

BASE_DIR = Path(__file__).parent
DEMO_DIR = BASE_DIR / "demo_data"
STATIC_DIR = BASE_DIR / "static"
SNAPSHOT_DIR = Path(os.environ.get("ESSTU_SNAPSHOT_DIR", BASE_DIR / "cache_store"))


def create_esstu_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
        ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT")
    return ctx


SSL_CONTEXT = create_esstu_ssl_context()


@dataclass(frozen=True)
class FetchedPage:
    html: str
    last_modified: Optional[str]
    source_mode: str
    checked_at: Optional[str]


def apply_page_status(payload, page):
    payload['last_modified'] = page.last_modified
    payload['source_mode'] = page.source_mode
    payload['source_checked_at'] = page.checked_at
    payload['is_stale_fallback'] = page.source_mode != 'portal_live'
    return payload


def save_snapshot(key: str, payload: Dict[str, Any]) -> None:
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in key)
    temporary = None
    try:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=SNAPSHOT_DIR, delete=False) as output:
            temporary = Path(output.name)
            json.dump(payload, output, ensure_ascii=False)
        temporary.replace(SNAPSHOT_DIR / f'{safe_name}.json')
    except OSError:
        LOGGER.warning('Could not save snapshot %s', key, exc_info=True)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def load_snapshot(key: str) -> Optional[Dict[str, Any]]:
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in key)
    path = SNAPSHOT_DIR / f'{safe_name}.json'
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        for item in [data, *data.get('teachers', [])]:
            item['is_stale_fallback'] = True
            item['source_mode'] = 'saved_snapshot'
        return data
    except (OSError, ValueError):
        LOGGER.warning('Could not load snapshot %s', key, exc_info=True)
        return None


def fetch_esstu_html_sync(relative_path: str, allow_group_fallback: bool = True) -> FetchedPage:
    clean_rel = relative_path.lstrip('/')
    if not re.fullmatch(r'(bakalavriat|spezialitet|zo1|zo2)/(?:\d+|Caf\d+|raspisan|craspisanEdt)\.htm', clean_rel):
        raise ValueError('Некорректный путь источника')
    try:
        req = urllib.request.Request(f'{ESSTU_BASE_URL}/{clean_rel}', headers={'User-Agent':'ESSTU-Schedule/2.4'})
        with urllib.request.urlopen(req, timeout=6, context=SSL_CONTEXT) as resp:
            return FetchedPage(resp.read().decode('cp1251', errors='replace'), resp.headers.get('Last-Modified'),
                               'portal_live', datetime.now(timezone.utc).isoformat())
    except (OSError, ValueError):
        LOGGER.warning('Portal unavailable for %s; trying saved source', clean_rel, exc_info=True)
        local_file = DEMO_DIR / clean_rel
        if local_file.is_file():
            meta = source_metadata(DEMO_DIR).get(clean_rel, {})
            return FetchedPage(local_file.read_bytes().decode('cp1251', errors='replace'), meta.get('last_modified'),
                               'local_fallback', meta.get('retrieved_at'))
        raise RuntimeError(f'Источник {clean_rel} недоступен')


def service_status() -> Dict[str, Any]:
    now_uu = datetime.now(timezone(timedelta(hours=8)))
    return {
        "university": "ВСГУТУ",
        "timezone": "Asia/Irkutsk (UTC+8)",
        "server_time_ulan_ude": now_uu.isoformat(),
        **get_week_num(now_uu),
    }


@singleflight
def service_groups(section: str = "bakalavriat", force_refresh: bool = False) -> Dict[str, Any]:
    if section not in SECTIONS:
        raise ValueError("Неизвестный раздел расписания")
    cache_key, now = f"groups:{section}", time.time()
    cached = CACHE.get(cache_key, CACHE_TTL_SECONDS)
    if not force_refresh and cached is not None:
        return cached
    try:
        page = fetch_esstu_html_sync(f"{section}/raspisan.htm", allow_group_fallback=False)
        html, last_mod = page.html, page.last_modified
        groups = parse_groups_list_html(html, section=section)
        if not groups:
            raise ValueError('Источник не содержит каталог групп')
        payload = {
            "section": section,
            "section_title": SECTIONS[section],
            "last_modified": last_mod,
            "count": len(groups),
            "groups": groups,
        }
        apply_page_status(payload, page)
        CACHE.put(cache_key, payload)
        save_snapshot(cache_key, payload)
        return payload
    except Exception:
        snap = load_snapshot(cache_key)
        if snap:
            return snap
        raise


def resolve_group_file_id(section: str, group_id: str, group_name: Optional[str] = None, force_refresh: bool = False) -> Tuple[str, str]:
    clean_id = unquote(group_id).replace(".htm", "").strip()
    target_name = unquote(group_name or "").strip()
    try:
        groups_list = service_groups(section, force_refresh=force_refresh).get("groups", [])
        search_norms = []
        if target_name:
            search_norms.append(normalize_group_name(target_name))
        if not clean_id.isdigit():
            search_norms.append(normalize_group_name(clean_id))
        for norm_q in search_norms:
            for g in groups_list:
                if g.get("norm_name") == norm_q:
                    return g["id"], g["name"]
        for g in groups_list:
            if g["id"] == clean_id:
                return g["id"], g["name"]
    except Exception:
        LOGGER.warning("Source lookup failed", exc_info=True)
    return clean_id, target_name or clean_id


@singleflight
def service_schedule(section: str, group_id: str, group_name: Optional[str] = None) -> Dict[str, Any]:
    if section not in SECTIONS:
        raise ValueError("Неизвестный раздел расписания")
    actual_id, expected_name = resolve_group_file_id(section, group_id, group_name, force_refresh=False)
    if not re.fullmatch(r"\d{1,6}", actual_id):
        raise ValueError("Группа не найдена в каталоге")
    norm_expected = normalize_group_name(expected_name) if expected_name else ""
    cache_key = f"sched:{section}:{actual_id}"
    snapshot_key = f"sched_{section}_{norm_expected or actual_id}"
    now = time.time()

    cached = CACHE.get(cache_key, CACHE_TTL_SECONDS)
    if cached is not None:
        if not norm_expected or cached.get("norm_group_name") == norm_expected:
            return cached

    try:
        page = fetch_esstu_html_sync(f"{section}/{actual_id}.htm")
        html, last_mod = page.html, page.last_modified
        schedule = parse_group_schedule_html(html, group_id=actual_id, section=section)
        if norm_expected and not norm_expected.isdigit() and schedule.get("norm_group_name") != norm_expected:
            new_id, _ = resolve_group_file_id(section, group_id, expected_name, force_refresh=True)
            if new_id != actual_id:
                actual_id = new_id
                page = fetch_esstu_html_sync(f"{section}/{actual_id}.htm")
                html, last_mod = page.html, page.last_modified
                schedule = parse_group_schedule_html(html, group_id=actual_id, section=section)
        if norm_expected and not norm_expected.isdigit() and schedule.get("norm_group_name") != norm_expected:
            raise ValueError("Имя группы не совпадает с источником")
        schedule["resolved_group_id"] = actual_id
        schedule["last_modified"] = last_mod
        schedule["week_now"] = get_week_num()
        stamp_schedule(schedule, source_metadata(DEMO_DIR), datetime.now(timezone.utc).isoformat())
        apply_page_status(schedule, page)
        CACHE.put(f"sched:{section}:{actual_id}", schedule)
        save_snapshot(snapshot_key, schedule)
        return schedule
    except Exception:
        snap = load_snapshot(snapshot_key)
        if snap:
            return snap
        raise


@singleflight
def service_saved_group_teachers():
    key = 'teachers_from_saved_groups'
    cached = CACHE.get(key, CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    schedules = []
    for section in SECTIONS:
        index = DEMO_DIR / section / 'raspisan.htm'
        known = parse_groups_list_html(index.read_bytes().decode('cp1251'), section) if index.exists() else []
        names = {group['id']: group['norm_name'] for group in known}
        for path in (DEMO_DIR / section).glob('*.htm'):
            if not path.stem.isdigit():
                continue
            try:
                expected = names.get(path.stem)
                schedule = parse_group_schedule_html(path.read_bytes().decode('cp1251', errors='replace'), group_id=path.stem, section=section)
                if expected and schedule.get('norm_group_name') == expected:
                    schedules.append(schedule)
            except Exception:
                LOGGER.warning("Saved schedule parse failed", exc_info=True)
                continue
    result = teachers_from_groups(schedules)
    CACHE.put(key, result)
    return result


@singleflight
def service_departments(section: str = "bakalavriat") -> Dict[str, Any]:
    if section not in ("bakalavriat", "spezialitet"):
        raise ValueError("Неизвестный раздел расписания")
    cache_key, now = f"depts:{section}", time.time()
    cached = CACHE.get(cache_key, CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    try:
        page = fetch_esstu_html_sync(f"{section}/craspisanEdt.htm", allow_group_fallback=False)
        html, last_mod = page.html, page.last_modified
        payload = {
            "section": section,
            "last_modified": last_mod,
            "institutes": parse_departments_list_html(html, section=section),
        }
        if not payload['institutes']:
            raise ValueError('Источник не содержит каталог кафедр')
        apply_page_status(payload, page)
        CACHE.put(cache_key, payload)
        save_snapshot(cache_key, payload)
        return payload
    except Exception:
        snap = load_snapshot(cache_key)
        if snap:
            return snap
        return {'section': section, 'institutes': departments_from_teachers(service_saved_group_teachers()),
                'source': 'group_schedules', 'partial': True}


@singleflight
def service_department_teachers(section: str, caf_id: str, merge: bool = True) -> Dict[str, Any]:
    if section not in ("bakalavriat", "spezialitet"):
        raise ValueError("Неизвестный раздел расписания")
    clean_caf = caf_id.replace(".htm", "")
    if not re.fullmatch(r"Caf\d{1,6}", clean_caf):
        raise ValueError("Некорректный идентификатор кафедры")
    cache_key, now = f"caf:{section}:{clean_caf}:{merge}", time.time()
    cached = CACHE.get(cache_key, CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    dept_name = clean_caf
    try:
        for inst in service_departments(section).get("institutes", []):
            for d in inst.get("departments", []):
                if d["caf_id"].lower() == clean_caf.lower():
                    dept_name = f"Кафедра «{d['name']}» ({inst['institute']})"
    except Exception:
        LOGGER.warning("Source lookup failed", exc_info=True)

    try:
        page = fetch_esstu_html_sync(f"{section}/{clean_caf}.htm", allow_group_fallback=False)
        html_p, last_mod = page.html, page.last_modified
        teachers_p = parse_department_teachers_html(html_p, caf_id=clean_caf, section=section, department_name=dept_name)
        if not teachers_p:
            raise ValueError('Источник не содержит расписания преподавателей')

        if merge:
            other = "spezialitet" if section == "bakalavriat" else "bakalavriat"
            try:
                secondary_page = fetch_esstu_html_sync(f"{other}/{clean_caf}.htm", allow_group_fallback=False)
                html_s = secondary_page.html
                sec_map = {
                    t["teacher_key"]: t
                    for t in parse_department_teachers_html(html_s, caf_id=clean_caf, section=other, department_name=dept_name)
                }
                teachers_p = [merge_teacher_schedules(t, sec_map.get(t["teacher_key"])) for t in teachers_p]
                primary_keys = {t['teacher_key'] for t in teachers_p}
                teachers_p.extend(t for key, t in sec_map.items() if key not in primary_keys)
            except Exception:
                LOGGER.warning("Secondary department unavailable", exc_info=True)

        for teacher in teachers_p:
            stamp_schedule(teacher, source_metadata(DEMO_DIR), datetime.now(timezone.utc).isoformat())
            apply_page_status(teacher, page if teacher.get("section") == section else secondary_page)
        payload = {
            "caf_id": clean_caf,
            "department_name": dept_name,
            "section": section,
            "last_modified": last_mod,
            "teachers": teachers_p,
        }
        apply_page_status(payload, page)
        CACHE.put(cache_key, payload)
        save_snapshot(cache_key, payload)
        return payload
    except Exception:
        snap = load_snapshot(cache_key)
        if snap:
            return snap
        raise


@singleflight
def service_all_teachers(section: str = "bakalavriat") -> Dict[str, Any]:
    if section not in ("bakalavriat", "spezialitet"):
        raise ValueError("Для раздела нет каталога кафедр")
    cache_key, now = f"all_teachers:{section}", time.time()
    cached = CACHE.get(cache_key, CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    all_t, seen = [], set()
    try:
        for inst in service_departments(section).get("institutes", []):
            for dept in inst.get("departments", []):
                try:
                    for t in service_department_teachers(section, dept["caf_id"], merge=True).get("teachers", []):
                        all_t.append(t)
                except Exception:
                    LOGGER.warning("Department fetch failed", exc_info=True)
                    continue

        all_t = combine_teacher_catalog(all_t, service_saved_group_teachers())
        payload = {"count": len(all_t), "teachers": all_t}
        CACHE.put(cache_key, payload)
        save_snapshot(cache_key, payload)
        return payload
    except Exception:
        snap = load_snapshot(cache_key)
        if snap:
            return snap
        raise


@singleflight
def service_rooms_index() -> Dict[str, Any]:
    key = 'rooms_index_all'
    now = time.time()
    cached = CACHE.get(key, CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    schedules = []
    errors = []
    for section in SECTIONS:
        try:
            if section in ('bakalavriat', 'spezialitet'):
                schedules.extend(service_all_teachers(section).get('teachers', []))
            for group in service_groups(section).get('groups', []):
                try:
                    schedules.append(service_schedule(section, group['id'], group.get('name')))
                except Exception:
                    errors.append(f"{section}/{group['id']}")
        except Exception:
            errors.append(section)
    payload = build_rooms_index(schedules)
    payload['failed_sources'] = errors
    if not schedules:
        raise RuntimeError('Не удалось загрузить расписания для индекса аудиторий')
    CACHE.put(key, payload)
    return payload


class ESSTURequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Any, status: int = 200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if self.command == 'GET':
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        if status == 405:
            self.send_header('Allow', 'GET, OPTIONS')
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        if self.headers.get('Access-Control-Request-Method', 'GET') not in ('GET', 'OPTIONS'):
            return self._send_json({'error':'Публичный сервер доступен только для чтения'}, status=405)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header('Allow', 'GET, OPTIONS')
        self.end_headers()

    def do_GET(self):
        if urlparse(self.path).path == '/api/rooms':
            try:
                return self._send_json(service_rooms_index())
            except Exception as exc:
                return self._send_json({'error': str(exc)}, status=503)
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        try:
            if path == "/api/status":
                return self._send_json(service_status())
            if path == "/api/groups":
                refresh = qs.get("refresh", ["false"])[0].lower() == "true"
                return self._send_json(service_groups(qs.get("section", ["bakalavriat"])[0], force_refresh=refresh))
            if path.startswith("/api/schedule/"):
                parts = [p for p in path.split("/") if p]
                if len(parts) != 4:
                    return self._send_json({"error":"Ожидается /api/schedule/section/group"}, status=400)
                group_name = qs.get("group_name", [None])[0]
                return self._send_json(service_schedule(parts[2], parts[3], group_name=group_name))
            if path == "/api/departments":
                return self._send_json(service_departments(qs.get("section", ["bakalavriat"])[0]))
            if path.startswith("/api/department/"):
                parts = [p for p in path.split("/") if p]
                if len(parts) != 4:
                    return self._send_json({"error":"Ожидается /api/department/section/caf"}, status=400)
                merge = qs.get("merge", ["true"])[0].lower() != "false"
                return self._send_json(service_department_teachers(parts[2], parts[3], merge=merge))
            if path == "/api/teachers/all":
                return self._send_json(service_all_teachers(qs.get("section", ["bakalavriat"])[0]))

            if path.startswith('/api/'):
                return self._send_json({'error':'Not found'}, status=404)
            rel = 'index.html' if path in ('', '/') else unquote(path).lstrip('/')
            file_path = (STATIC_DIR / rel).resolve()
            if not file_path.is_relative_to(STATIC_DIR.resolve()) or not file_path.is_file():
                return self._send_json({'error':'Static file not found'}, status=404)
            content = file_path.read_bytes()
            etag = '"' + hashlib.sha256(content).hexdigest() + '"'
            mime = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            self.send_response(304 if self.headers.get('If-None-Match') == etag else 200)
            self.send_header('ETag', etag)
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if self.headers.get('If-None-Match') == etag:
                self.end_headers()
                return
            text_mime = mime.startswith('text/') or mime in ('application/javascript','application/json','image/svg+xml','application/manifest+json')
            self.send_header('Content-Type', mime + ('; charset=utf-8' if text_mime else ''))
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except ValueError as error:
            self._send_json({'error':str(error)}, status=400)
        except Exception:
            LOGGER.exception('Request failed: %s', path)
            self._send_json({'error':'Источник временно недоступен'}, status=503)

    def do_POST(self):
        # Public service is read-only. Never read/parse/write an incoming body.
        self.close_connection = True
        try:
            lengths = self.headers.get_all('Content-Length', [])
            if len(lengths) > 1 or self.headers.get('Transfer-Encoding'):
                raise ValueError('Неоднозначная длина запроса')
            if lengths and not re.fullmatch(r'[0-9]+', lengths[0]):
                raise ValueError('Недопустимая длина запроса')
            length = int(lengths[0]) if lengths else 0
            if length < 0 or length > 8192:
                raise ValueError('Недопустимый размер запроса')
            return self._send_json({'error':'Публичный сервер доступен только для чтения'}, status=405)
        except ValueError:
            return self._send_json({'error':'Недопустимая длина запроса'}, status=400)
        except Exception:
            LOGGER.exception('POST rejection failed')
            return self._send_json({'error':'Не удалось обработать запрос'}, status=500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Сервер ВСГУТУ Расписание Live запущен: http://localhost:{port}")
    try:
        ThreadingHTTPServer(("0.0.0.0", port), ESSTURequestHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
