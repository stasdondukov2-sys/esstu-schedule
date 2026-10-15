import json
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
    save_teacher_meta_entry,
)

CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_TTL_SECONDS = 900

BASE_DIR = Path(__file__).parent
DEMO_DIR = BASE_DIR / "demo_data"
STATIC_DIR = BASE_DIR / "static"
SNAPSHOT_DIR = BASE_DIR / "cache_store"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def create_esstu_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
        ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT")
    return ctx


SSL_CONTEXT = create_esstu_ssl_context()


def save_snapshot(key: str, payload: Dict[str, Any]) -> None:
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in key)
    try:
        (SNAPSHOT_DIR / f"{safe_name}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def load_snapshot(key: str) -> Optional[Dict[str, Any]]:
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in key)
    path = SNAPSHOT_DIR / f"{safe_name}.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data["is_stale_fallback"] = True
            data["last_modified"] = "⚠️ Сайт ВСГУТУ обновляется — показана сохранённая рабочая копия"
            return data
        except Exception:
            return None
    return None


def fetch_esstu_html_sync(relative_path: str, allow_group_fallback: bool = True) -> Tuple[str, str]:
    clean_rel = relative_path.lstrip("/")
    url = f"{ESSTU_BASE_URL}/{clean_rel}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ESSTU-Schedule-PWA/2.1"})
        with urllib.request.urlopen(req, timeout=6, context=SSL_CONTEXT) as resp:
            raw = resp.read()
            html = raw.decode("cp1251", errors="replace")
            last_mod = resp.headers.get("Last-Modified") or "Прямая синхронизация с portal.esstu.ru"
            return html, last_mod
    except Exception:
        local_file = DEMO_DIR / clean_rel
        if local_file.exists():
            return local_file.read_bytes().decode("cp1251", errors="replace"), "Локальный кэш ВСГУТУ (cp1251)"
        raise FileNotFoundError(f"Страница {clean_rel} не найдена")


def service_status() -> Dict[str, Any]:
    now_uu = datetime.now(timezone(timedelta(hours=8)))
    return {
        "university": "ВСГУТУ",
        "timezone": "Asia/Irkutsk (UTC+8)",
        "server_time_ulan_ude": now_uu.isoformat(),
        **get_week_num(now_uu),
    }


def service_groups(section: str = "bakalavriat", force_refresh: bool = False) -> Dict[str, Any]:
    if section not in SECTIONS:
        section = "bakalavriat"
    cache_key, now = f"groups:{section}", time.time()
    if not force_refresh and cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        return CACHE[cache_key][1]
    try:
        html, last_mod = fetch_esstu_html_sync(f"{section}/raspisan.htm", allow_group_fallback=False)
        groups = parse_groups_list_html(html, section=section)
        payload = {
            "section": section,
            "section_title": SECTIONS[section],
            "last_modified": last_mod,
            "count": len(groups),
            "groups": groups,
        }
        CACHE[cache_key] = (now, payload)
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
        pass
    return clean_id, target_name or clean_id


def service_schedule(section: str, group_id: str, group_name: Optional[str] = None) -> Dict[str, Any]:
    if section not in SECTIONS:
        section = "bakalavriat"
    actual_id, expected_name = resolve_group_file_id(section, group_id, group_name, force_refresh=False)
    norm_expected = normalize_group_name(expected_name) if expected_name else ""
    cache_key = f"sched:{section}:{actual_id}"
    snapshot_key = f"sched_{section}_{norm_expected or actual_id}"
    now = time.time()

    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        cached = CACHE[cache_key][1]
        if not norm_expected or cached.get("norm_group_name") == norm_expected:
            return cached

    try:
        html, last_mod = fetch_esstu_html_sync(f"{section}/{actual_id}.htm")
        schedule = parse_group_schedule_html(html, group_id=actual_id, section=section)
        if norm_expected and not norm_expected.isdigit() and schedule.get("norm_group_name") != norm_expected:
            new_id, _ = resolve_group_file_id(section, group_id, expected_name, force_refresh=True)
            if new_id != actual_id:
                actual_id = new_id
                html, last_mod = fetch_esstu_html_sync(f"{section}/{actual_id}.htm")
                schedule = parse_group_schedule_html(html, group_id=actual_id, section=section)
        schedule["resolved_group_id"] = actual_id
        schedule["last_modified"] = last_mod
        schedule["week_now"] = get_week_num()
        stamp_schedule(schedule, source_metadata(DEMO_DIR), datetime.now(timezone.utc).isoformat())
        if not last_mod.startswith('Локальный'):
            schedule['source_checked_at'] = datetime.now(timezone.utc).isoformat()
            schedule['source_mode'] = 'portal_live'
        CACHE[f"sched:{section}:{actual_id}"] = (now, schedule)
        save_snapshot(snapshot_key, schedule)
        return schedule
    except Exception:
        snap = load_snapshot(snapshot_key)
        if snap:
            return snap
        raise


def service_saved_group_teachers():
    key = 'teachers_from_saved_groups'
    if key in CACHE and time.time() - CACHE[key][0] < CACHE_TTL_SECONDS:
        return CACHE[key][1]
    schedules = []
    for section in SECTIONS:
        for path in (DEMO_DIR / section).glob('*.htm'):
            if not path.stem.isdigit():
                continue
            try:
                schedules.append(parse_group_schedule_html(path.read_bytes().decode('cp1251', errors='replace'),
                                                          group_id=path.stem, section=section))
            except Exception:
                continue
    result = teachers_from_groups(schedules)
    CACHE[key] = (time.time(), result)
    return result


def service_departments(section: str = "bakalavriat") -> Dict[str, Any]:
    if section not in ("bakalavriat", "spezialitet"):
        section = "bakalavriat"
    cache_key, now = f"depts:{section}", time.time()
    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        return CACHE[cache_key][1]

    try:
        html, last_mod = fetch_esstu_html_sync(f"{section}/craspisanEdt.htm", allow_group_fallback=False)
        payload = {
            "section": section,
            "last_modified": last_mod,
            "institutes": parse_departments_list_html(html, section=section),
        }
        CACHE[cache_key] = (now, payload)
        save_snapshot(cache_key, payload)
        return payload
    except Exception:
        snap = load_snapshot(cache_key)
        if snap:
            return snap
        return {'section': section, 'institutes': departments_from_teachers(service_saved_group_teachers()),
                'source': 'group_schedules', 'partial': True}


def service_department_teachers(section: str, caf_id: str, merge: bool = True) -> Dict[str, Any]:
    if section not in ("bakalavriat", "spezialitet"):
        section = "bakalavriat"
    clean_caf = caf_id.replace(".htm", "")
    cache_key, now = f"caf:{section}:{clean_caf}:{merge}", time.time()
    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        return CACHE[cache_key][1]

    dept_name = clean_caf
    try:
        for inst in service_departments(section).get("institutes", []):
            for d in inst.get("departments", []):
                if d["caf_id"].lower() == clean_caf.lower():
                    dept_name = f"Кафедра «{d['name']}» ({inst['institute']})"
    except Exception:
        pass

    try:
        html_p, last_mod = fetch_esstu_html_sync(f"{section}/{clean_caf}.htm", allow_group_fallback=False)
        teachers_p = parse_department_teachers_html(html_p, caf_id=clean_caf, section=section, department_name=dept_name)

        if merge:
            other = "spezialitet" if section == "bakalavriat" else "bakalavriat"
            try:
                html_s, _ = fetch_esstu_html_sync(f"{other}/{clean_caf}.htm", allow_group_fallback=False)
                sec_map = {
                    t["teacher_key"]: t
                    for t in parse_department_teachers_html(html_s, caf_id=clean_caf, section=other, department_name=dept_name)
                }
                teachers_p = [merge_teacher_schedules(t, sec_map.get(t["teacher_key"])) for t in teachers_p]
                primary_keys = {t['teacher_key'] for t in teachers_p}
                teachers_p.extend(t for key, t in sec_map.items() if key not in primary_keys)
            except Exception:
                pass

        for teacher in teachers_p:
            stamp_schedule(teacher, source_metadata(DEMO_DIR), datetime.now(timezone.utc).isoformat())
            if not last_mod.startswith('Локальный') and teacher.get('section') == section:
                teacher['source_checked_at'] = datetime.now(timezone.utc).isoformat()
                teacher['source_mode'] = 'portal_live'
        payload = {
            "caf_id": clean_caf,
            "department_name": dept_name,
            "section": section,
            "last_modified": last_mod,
            "teachers": teachers_p,
        }
        CACHE[cache_key] = (now, payload)
        save_snapshot(cache_key, payload)
        return payload
    except Exception:
        snap = load_snapshot(cache_key)
        if snap:
            return snap
        raise


def service_all_teachers(section: str = "bakalavriat") -> Dict[str, Any]:
    cache_key, now = f"all_teachers:{section}", time.time()
    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        return CACHE[cache_key][1]

    all_t, seen = [], set()
    try:
        for inst in service_departments(section).get("institutes", []):
            for dept in inst.get("departments", []):
                try:
                    for t in service_department_teachers(section, dept["caf_id"], merge=True).get("teachers", []):
                        all_t.append(t)
                except Exception:
                    continue

        all_t = combine_teacher_catalog(all_t, service_saved_group_teachers())
        payload = {"count": len(all_t), "teachers": all_t}
        CACHE[cache_key] = (now, payload)
        save_snapshot(cache_key, payload)
        return payload
    except Exception:
        snap = load_snapshot(cache_key)
        if snap:
            return snap
        raise


def service_rooms_index() -> Dict[str, Any]:
    key = 'rooms_index_all'
    now = time.time()
    if key in CACHE and now - CACHE[key][0] < CACHE_TTL_SECONDS:
        return CACHE[key][1]
    schedules = []
    errors = []
    for section in SECTIONS:
        try:
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
    CACHE[key] = (time.time(), payload)
    return payload


def service_update_teacher_meta(data: Dict[str, Any]) -> Dict[str, Any]:
    t_key = data.get("teacher_key", "")
    upd = {k: str(data[k]).strip() for k in ("photo", "full_name", "degree", "building") if data.get(k)}
    saved = save_teacher_meta_entry(t_key, upd)
    CACHE.clear()
    return {"status": "ok", "teacher_key": normalize_teacher_key(t_key), "meta": saved}


class ESSTURequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Any, status: int = 200):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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
                group_name = qs.get("group_name", [None])[0]
                return self._send_json(service_schedule(parts[2], parts[3], group_name=group_name))
            if path == "/api/departments":
                return self._send_json(service_departments(qs.get("section", ["bakalavriat"])[0]))
            if path.startswith("/api/department/"):
                parts = [p for p in path.split("/") if p]
                merge = qs.get("merge", ["true"])[0].lower() != "false"
                return self._send_json(service_department_teachers(parts[2], parts[3], merge=merge))
            if path == "/api/teachers/all":
                return self._send_json(service_all_teachers(qs.get("section", ["bakalavriat"])[0]))

            # Static file serving
            rel = "index.html" if path in ("", "/") else path.lstrip("/")
            file_path = (STATIC_DIR / rel).resolve()
            if not file_path.is_file() or not str(file_path).startswith(str(STATIC_DIR.resolve())):
                file_path = STATIC_DIR / "index.html"

            if not file_path.is_file():
                return self._send_json({"error": "Static file not found"}, status=404)

            content = file_path.read_bytes()
            mime, _ = mimetypes.guess_type(str(file_path))
            self.send_response(200)
            self.send_header("Content-Type", f"{mime or 'text/html'}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json({"error": str(e)}, status=500)

    def do_POST(self):
        if urlparse(self.path).path == "/api/teacher/meta":
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") if length > 0 else "{}")
            return self._send_json(service_update_teacher_meta(data))
        self._send_json({"error": "Not found"}, status=404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Сервер ВСГУТУ Расписание Live запущен: http://localhost:{port}")
    try:
        ThreadingHTTPServer(("0.0.0.0", port), ESSTURequestHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
