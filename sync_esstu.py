"""Refresh official department and group snapshots without generating test data."""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from parser import SECTIONS, parse_groups_list_html
from sync_departments import ROOT, fetch_page, sync as sync_departments


def sync_groups():
    manifest_path = ROOT / 'sources.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else {}
    targets, failures, successes = [], [], []
    for section in SECTIONS:
        relative = f'{section}/raspisan.htm'
        try:
            path, meta = fetch_page(relative)
            manifest[path] = meta
            successes.append(path)
        except Exception as exc:
            failures.append({'path': relative, 'error': str(exc)})
        index = ROOT / relative
        if index.exists():
            groups = parse_groups_list_html(index.read_bytes().decode('cp1251'), section)
            targets.extend(f"{section}/{g['id']}.htm" for g in groups if re.fullmatch(r'\d+', str(g['id'])))
    with ThreadPoolExecutor(max_workers=6) as pool:
        pending = {pool.submit(fetch_page, path): path for path in sorted(set(targets))}
        for future in as_completed(pending):
            try:
                path, meta = future.result()
                manifest[path] = meta
                successes.append(path)
            except Exception as exc:
                failures.append({'path': pending[future], 'error': str(exc)})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'downloaded': successes,
              'failed': failures, 'group_pages_expected': len(set(targets))}
    (ROOT / 'group-sync.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Group pages downloaded: {len(successes)}; failed: {len(failures)}")
    return report


if __name__ == '__main__':
    sync_departments()
    sync_groups()
