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


def allocate_wednesday_kickoff(catalog):
    # September 14 revision: retain every required video, cap Thursday at five.
    fixed = {
        0: ['bbguy-bloodgroups'],
        1: ['bbguy-acquiredb', 'bbguy-rhig', 'bbguy-leukoreduce', 'bbguy-irradiate',
            'gram-positive-cocci/lesson/staphylococcus-aureus'],
        2: ['bbguy-pretransfusion'], 3: ['morgan-bacteriology1'],
        4: ['bbguy-antibodyid1'], 6: ['bbguy-antibodyid2'],
        7: ['morgan-bacteriology2'], 8: ['bbguy-kell'], 9: ['bbguy-lewis'],
        10: ['bbguy-bombay'], 11: ['morgan-mycobacteriology'], 12: ['bbguy-dvariants'],
        14: ['bbguy-reactionworkup'], 15: ['bbguy-reactions'], 16: ['morgan-mycology1'],
        17: ['bbguy-ttd1'], 18: ['bbguy-ttd2'], 20: ['morgan-mycology2'],
        22: ['morgan-parasitology'], 24: ['morgan-virology'],
        27: ['bbguy-lastminute-part1'], 28: ['bbguy-lastminute-part2'],
        30: ['bbguy-lastminute-part3'],
        5: ['acute-kidney-injury-1/lesson/renal-function-tests-acute-kidney-injury-aki'],
        13: ['volume-electrolyte-acid-base-disorders/lesson/osmolality-sodium-disorders'],
        19: ['volume-electrolyte-acid-base-disorders/lesson/acid-base-disorders'],
        21: ['pharmacokinetic-basics/lesson/plasma-concentration-therapeutic-range',
             'elimination/lesson/clearance-area-under-the-curve',
             'elimination/lesson/elimination-rate-constant-half-life-steady-state'],
    }
    reserved = {key for keys in fixed.values() for key in keys}
    micro = [key for key, v in catalog.items() if v['course'] == 'Micro' and key not in reserved]
    sessions = [{'date': '2026-09-15', 'kind': 'cancelled', 'lessons': [],
                 'note': 'Tuesday video block cancelled; video study starts Wednesday September 16.'}]
    for offset in range(33):
        lessons = list(fixed.get(offset, []))
        minutes = sum(catalog[key]['minutes'] for key in lessons)
        while offset < 31 and offset != 1:
            key = next((key for key in micro if minutes + catalog[key]['minutes'] <= 80), None)
            if key is None:
                break
            micro.remove(key)
            lessons.append(key)
            minutes += catalog[key]['minutes']
        session = {'date': (date(2026, 9, 16) + timedelta(days=offset)).isoformat(),
                   'kind': 'light' if offset >= 31 else 'watch' if lessons else 'review',
                   'lessons': lessons}
        if offset == 0:
            session.update(label='Video kickoff', note='Wednesday video launch. Morning question sessions start Friday September 18.')
        elif offset == 1:
            session.update(label='Five-video review', note='Thursday: exactly these five short videos, approximately 54 minutes. Rewatch familiar topics or preview them if new, then briefly recall the main distinctions. No extra video assignment tonight. These count once toward the complete video plan; no completion is assumed.')
        elif offset == 29:
            session['note'] = 'This is now a watch night after the later launch, replacing the former video catch-up evening. The morning timed question block and repeat-review reserve are unchanged.'
        sessions.append(session)
    if micro:
        raise ValueError('Full Micro does not fit the revised dates')
    return {'source_checked': '2026-09-13', 'revised_on': '2026-09-14',
            'revision': 'Wednesday video launch, Thursday five-video review, Friday morning kickoff',
            'start': '21:00', 'duration_minutes': 90, 'max_video_minutes': 80,
            'optional_lessons': [key for key, v in catalog.items() if v['course'] in {'Path', 'Pharm'} and key not in reserved],
            'sessions': sessions}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--profile', choices=['original-sketchy', 'complete-bbguy', 'wednesday-kickoff'], default='original-sketchy')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite dated assignments; edit upcoming dates explicitly')
    result = (allocate_wednesday_kickoff(read_all_videos()) if args.profile == 'wednesday-kickoff'
              else allocate_complete_bbguy(read_all_videos()) if args.profile == 'complete-bbguy'
              else allocate(read_video_catalog(ROOT / 'video_catalog.tsv')))
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(f"Created {len(result['sessions'])} nightly assignments")
