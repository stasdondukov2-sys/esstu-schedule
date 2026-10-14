import json
import mimetypes
import os
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Any, Tuple
from urllib.parse import urlparse, parse_qs
import urllib.request
import ssl

from parser import (
    ESSTU_BASE_URL,
    SECTIONS,
    get_week_num,
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

# Create SSL context that allows portal access if cert is legacy
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def fetch_esstu_html_sync(relative_path: str, allow_group_fallback: bool = True) -> Tuple[str, str]:
    clean_rel = relative_path.lstrip("/")
    url = f"{ESSTU_BASE_URL}/{clean_rel}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ESSTU-Schedule-PWA/2.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        with urllib.request.urlopen(req, timeout=8, context=ssl_ctx) as resp:
            raw = resp.read()
            html = raw.decode("cp1251", errors="replace")
            last_mod = resp.headers.get("Last-Modified") or "Прямая синхронизация с portal.esstu.ru"
            return html, last_mod
    except Exception as e:
        local_file = DEMO_DIR / clean_rel
        if local_file.exists():
            return local_file.read_bytes().decode("cp1251", errors="replace"), "Локальный кэш ВСГУТУ (cp1251)"
        if allow_group_fallback and not clean_rel.lower().endswith("craspisanedt.htm") and "caf" not in clean_rel.lower():
            fallback = DEMO_DIR / "bakalavriat" / "1.htm"
            if fallback.exists():
                return fallback.read_bytes().decode("cp1251", errors="replace"), "Локальный кэш ВСГУТУ"
        raise FileNotFoundError(f"Страница {clean_rel} не найдена на портале и в кэше: {e}")


def service_status() -> Dict[str, Any]:
    now_uu = datetime.now(timezone(timedelta(hours=8)))
    return {
        "university": "ВСГУТУ",
        "timezone": "Asia/Irkutsk (UTC+8)",
        "server_time_ulan_ude": now_uu.isoformat(),
        **get_week_num(now_uu),
    }


def service_groups(section: str = "bakalavriat") -> Dict[str, Any]:
    if section not in SECTIONS:
        section = "bakalavriat"
    cache_key, now = f"groups:{section}", time.time()
    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        return CACHE[cache_key][1]

    html, last_mod = fetch_esstu_html_sync(f"{section}/raspisan.htm")
    groups = parse_groups_list_html(html, section=section)
    payload = {
        "section": section,
        "section_title": SECTIONS[section],
        "last_modified": last_mod,
        "count": len(groups),
        "groups": groups,
    }
    CACHE[cache_key] = (now, payload)
    return payload


def service_schedule(section: str, group_id: str) -> Dict[str, Any]:
    if section not in SECTIONS:
        section = "bakalavriat"
    clean_id = group_id.replace(".htm", "")
    cache_key, now = f"sched:{section}:{clean_id}", time.time()
    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        return CACHE[cache_key][1]

    html, last_mod = fetch_esstu_html_sync(f"{section}/{clean_id}.htm")
    schedule = parse_group_schedule_html(html, group_id=clean_id, section=section)
    schedule["last_modified"] = last_mod
    schedule["week_now"] = get_week_num()
    CACHE[cache_key] = (now, schedule)
    return schedule


def service_departments(section: str = "bakalavriat") -> Dict[str, Any]:
    if section not in ("bakalavriat", "spezialitet"):
        section = "bakalavriat"
    cache_key, now = f"depts:{section}", time.time()
    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        return CACHE[cache_key][1]

    html, last_mod = fetch_esstu_html_sync(f"{section}/craspisanEdt.htm", allow_group_fallback=False)
    payload = {
        "section": section,
        "last_modified": last_mod,
        "institutes": parse_departments_list_html(html, section=section),
    }
    CACHE[cache_key] = (now, payload)
    return payload


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
        except Exception:
            pass

    payload = {
        "caf_id": clean_caf,
        "department_name": dept_name,
        "section": section,
        "last_modified": last_mod,
        "teachers": teachers_p,
    }
    CACHE[cache_key] = (now, payload)
    return payload


def service_all_teachers(section: str = "bakalavriat") -> Dict[str, Any]:
    cache_key, now = f"all_teachers:{section}", time.time()
    if cache_key in CACHE and (now - CACHE[cache_key][0]) < CACHE_TTL_SECONDS:
        return CACHE[cache_key][1]

    all_t, seen = [], set()
    for inst in service_departments(section).get("institutes", []):
        for dept in inst.get("departments", []):
            try:
                for t in service_department_teachers(section, dept["caf_id"], merge=True).get("teachers", []):
                    if t["teacher_key"] not in seen:
                        seen.add(t["teacher_key"])
                        all_t.append(t)
            except Exception:
                continue

    payload = {"count": len(all_t), "teachers": all_t}
    CACHE[cache_key] = (now, payload)
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
        parsed = urlparse(self.path)
        path, qs = parsed.path, parse_qs(parsed.query)
        try:
            if path == "/api/status":
                return self._send_json(service_status())
            if path == "/api/groups":
                return self._send_json(service_groups(qs.get("section", ["bakalavriat"])[0]))
            if path.startswith("/api/schedule/"):
                parts = [p for p in path.split("/") if p]
                return self._send_json(service_schedule(parts[2], parts[3]))
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
