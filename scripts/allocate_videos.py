#!/usr/bin/env python3
"""Create an initial dated allocation; normal calendar builds never reallocate it."""

import argparse
from collections import deque
from datetime import date, timedelta
import json
from pathlib import Path

from generate_calendar import ROOT, read_video_catalog, read_all_videos


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


def allocate_complete_bbguy(catalog):
    # Explicit future-only revision agreed September 13; ordinary builds never run this.
    lecture_days = {
        0: ['bbguy-bloodgroups'], 2: ['bbguy-pretransfusion'],
        3: ['morgan-bacteriology1'], 4: ['bbguy-antibodyid1'],
        6: ['bbguy-antibodyid2'], 7: ['morgan-bacteriology2'],
        8: ['bbguy-kell'], 9: ['bbguy-lewis'], 10: ['bbguy-bombay'],
        11: ['morgan-mycobacteriology'], 12: ['bbguy-dvariants'],
        14: ['bbguy-acquiredb', 'bbguy-rhig', 'bbguy-leukoreduce', 'bbguy-irradiate'],
        15: ['bbguy-reactionworkup'], 16: ['bbguy-reactions'],
        17: ['morgan-mycology1'], 18: ['bbguy-ttd1'], 19: ['bbguy-ttd2'],
        21: ['morgan-mycology2'], 23: ['morgan-parasitology'], 25: ['morgan-virology'],
        28: ['bbguy-lastminute-part1'], 29: ['bbguy-lastminute-part2'],
        31: ['bbguy-lastminute-part3'],
    }
    supporting_days = {
        1: ['acute-kidney-injury-1/lesson/renal-function-tests-acute-kidney-injury-aki'],
        5: ['volume-electrolyte-acid-base-disorders/lesson/osmolality-sodium-disorders'],
        13: ['volume-electrolyte-acid-base-disorders/lesson/acid-base-disorders'],
        20: ['pharmacokinetic-basics/lesson/plasma-concentration-therapeutic-range',
             'elimination/lesson/clearance-area-under-the-curve',
             'elimination/lesson/elimination-rate-constant-half-life-steady-state'],
    }
    supporting = {key for keys in supporting_days.values() for key in keys}
    micro = deque(v['path'] for v in catalog.values() if v['course'] == 'Micro')
    sessions = []
    for offset in range(34):
        lessons = lecture_days.get(offset, []) + supporting_days.get(offset, [])
        minutes = sum(catalog[key]['minutes'] for key in lessons)
        while offset < 32:
            key = next((key for key in micro if minutes + catalog[key]['minutes'] <= 80), None)
            if key is None:
                break
            micro.remove(key)
            lessons.append(key)
            minutes += catalog[key]['minutes']
        sessions.append({'date': (date(2026, 9, 15) + timedelta(days=offset)).isoformat(),
                         'kind': 'light' if offset >= 32 else 'watch' if lessons else 'review',
                         'lessons': lessons})
    if micro:
        raise ValueError('Full Micro does not fit; do not silently drop lessons')
    return {'source_checked': '2026-09-13', 'revision': 'Complete BBGuy + Morgan + Micro; supersedes the original Path/Pharm-heavy future allocation',
            'start': '21:00', 'duration_minutes': 90, 'max_video_minutes': 80,
            'optional_lessons': [key for key, v in catalog.items() if v['course'] in {'Path', 'Pharm'} and key not in supporting],
            'sessions': sessions}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--profile', choices=['original-sketchy', 'complete-bbguy'], default='original-sketchy')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite dated assignments; edit upcoming dates explicitly')
    result = (allocate_complete_bbguy(read_all_videos()) if args.profile == 'complete-bbguy'
              else allocate(read_video_catalog(ROOT / 'video_catalog.tsv')))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Created {len(result['sessions'])} nightly assignments")
