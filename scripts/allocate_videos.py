#!/usr/bin/env python3
"""Create an initial dated allocation; normal calendar builds never reallocate it."""

import argparse
from collections import deque
from datetime import date, timedelta
import json
from pathlib import Path

from generate_calendar import ROOT, read_video_catalog


def allocate(catalog):
    queues = {course: [v for v in catalog.values() if v['course'] == course]
              for course in ('Micro', 'Path', 'Pharm')}
    # Bring hematology and antimicrobial mechanisms forward without splitting lessons.
    queues['Path'].sort(key=lambda v: 0 if v['path'].startswith((
        'microcytic-', 'normocytic-', 'coagulopathies-', 'myeloid-', 'lymphoid-')) else 1)
    queues['Pharm'].sort(key=lambda v: 0 if v['path'].startswith((
        'cell-wall-', 'inhibitors-of-bacterial-', 'antimycobacterials/',
        'other-antibiotics/', 'antifungals/')) else 1)
    totals = {c: sum(v['minutes'] for v in q) for c, q in queues.items()}
    used = dict.fromkeys(queues, 0)
    queues = {c: deque(q) for c, q in queues.items()}
    sessions = []
    start, finish = date(2026, 9, 15), date(2026, 10, 16)
    day = start
    while day <= finish:
        remaining = sum(totals[c] - used[c] for c in queues)
        days = (finish - day).days + 1
        target = min(80, (remaining + days - 1) // days + 4)
        lessons, minutes = [], 0
        while True:
            available = [c for c, q in queues.items() if q and minutes + q[0]['minutes'] <= target]
            if not available:
                break
            course = min(available, key=lambda c: used[c] / totals[c])
            video = queues[course].popleft()
            lessons.append(video['path'])
            minutes += video['minutes']
            used[course] += video['minutes']
        sessions.append({'date': day.isoformat(), 'kind': 'watch' if lessons else 'review', 'lessons': lessons})
        day += timedelta(days=1)
    if any(queues.values()):
        raise ValueError('Selected lessons do not fit; reduce scope or add approved time')
    for offset in (1, 2):
        sessions.append({'date': (finish + timedelta(days=offset)).isoformat(), 'kind': 'light', 'lessons': []})
    return {'source_checked': '2026-09-13', 'start': '21:00', 'duration_minutes': 90,
            'max_video_minutes': 80, 'sessions': sessions}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite dated assignments; edit upcoming dates explicitly')
    result = allocate(read_video_catalog(ROOT / 'video_catalog.tsv'))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Created {len(result['sessions'])} nightly assignments")
