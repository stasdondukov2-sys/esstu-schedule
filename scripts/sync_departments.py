"""Download only official department pages; retain the last good copy on failure."""
import json
import logging
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from esstu_schedule.parser import parse_departments_list_html, parse_groups_list_html
from esstu_schedule.data.repository import group_schedule as parse_group_schedule_html, department_schedules as parse_department_teachers_html


ROOT = Path(__file__).resolve().parents[1] / 'demo_data'
SECTIONS = ('bakalavriat', 'spezialitet')


def fetch_page(relative):
    request = urllib.request.Request('https://portal.esstu.ru/' + relative,
                                     headers={'User-Agent': 'ESSTU-Schedule/2.4'})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read()
        modified = response.headers.get('Last-Modified')
    html = raw.decode('cp1251', errors='replace')
    section, name = relative.split('/')
    if name == 'craspisanEdt.htm':
        valid = parse_departments_list_html(html, section)
    elif name == 'raspisan.htm':
        valid = parse_groups_list_html(html, section)
    elif re.fullmatch(r'\d+\.htm', name):
        schedule = parse_group_schedule_html(html, name[:-4], section)
        valid = not schedule.get('is_incomplete') and bool(schedule['weeks']['1'] or schedule['weeks']['2'])
    else:
        valid = parse_department_teachers_html(html, name[:-4], section)
    if isinstance(valid, list) and any(item.get('is_incomplete') for item in valid):
        valid = False
    if not valid:
        raise ValueError('Page contains no valid schedule data')
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return relative, {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'last_modified': modified}


def sync():
    manifest_path = ROOT / 'sources.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    targets, failures, successes = [], [], []
    for section in SECTIONS:
        relative = f'{section}/craspisanEdt.htm'
        try:
            path, meta = fetch_page(relative)
            manifest[path] = meta
            successes.append(path)
        except Exception as exc:
            logging.getLogger(__name__).exception('Source synchronization failed: %s', relative)
            failures.append({'path': relative, 'error': str(exc)})
        index = ROOT / relative
        if index.exists():
            for institute in parse_departments_list_html(index.read_bytes().decode('cp1251'), section):
                for department in institute['departments']:
                    if re.fullmatch(r'Caf\d+', department['caf_id'], re.I):
                        targets.append(f"{section}/{department['caf_id']}.htm")
    with ThreadPoolExecutor(max_workers=6) as pool:
        pending = {pool.submit(fetch_page, path): path for path in sorted(set(targets))}
        for future in as_completed(pending):
            try:
                path, meta = future.result()
                manifest[path] = meta
                successes.append(path)
            except Exception as exc:
                logging.getLogger(__name__).exception('Source synchronization failed: %s', pending[future])
                failures.append({'path': pending[future], 'error': str(exc)})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'downloaded': successes,
              'failed': failures, 'department_pages_expected': len(set(targets))}
    (ROOT / 'department-sync.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Official pages downloaded: {len(successes)}; failed: {len(failures)}")


if __name__ == '__main__':
    sync()
