# CP Boards Calendar

Daily protected study blocks for the CP-only examination on October 19, 2026.

## Calendar

- [Study calendar](https://rowlandpettit.com/cp-boards-calendar/)
- [Subscribe in Apple Calendar](webcal://rowlandpettit.com/cp-boards-calendar/cp-study.ics)
- [HTTPS calendar feed](https://rowlandpettit.com/cp-boards-calendar/cp-study.ics)
- [RSS feed](https://rowlandpettit.com/cp-boards-calendar/rss.xml), for RSS readers rather than Calendar

The 35 morning blocks run September 14-October 18, 5:00-7:00 AM as floating local times. Another 34 separate video blocks run September 15-October 18, 9:00-10:30 PM, in the same subscription. October 15 is catch-up; the final two evenings are optional light recall. Each occurrence has a stable date-based ID and countdown to October 19; no event is generated on examination day.

Event notes include the objective, a realistic two-hour routine, selected materials, resource links and the adaptation policy. The main aim is learning from questions and recurring gaps, not completing every bank and deck. [Study strategy](context.md).

## Edit and Sync

Edit `plan.toml` and the dated quotas in `question_plan.csv`, then run `make validate`, commit and push to `main`. GitHub Actions regenerates the public feeds and deploys GitHub Pages. Calendar subscribers receive updates on their configured refresh schedule; updates are not instantaneous.

## Two-Bank Workload

- Required first pass: 885 PathDojo + 157 ASCP CP + 54 ASCP shared hematopathology = **1,096 unique questions**, September 14-October 4.
- September 14: 54 new. September 15-16: 53 new daily. September 17-October 4: 52 new daily. Each date lists the exact bank split.
- September 16-October 4: 8 PathDojo + 2 ASCP first redos daily, 190 total. These are estimated slots, not actual results.
- October 5-12: clear the other 468 estimated first redos, 58-60 daily. Under the hypothetical 60% incorrect assumption, first-redo capacity totals **658** (531 PathDojo, 127 ASCP).
- October 13-16: **320 additional repeat/gap slots**, up to 80 daily. October 15 includes a 55-question timed block within its 80 slots, not in addition. October 17-18 remains light.
- The morning now prioritizes questions and explanations, with 15 minutes of targeted reading. Daily quotas are whole-day targets: expect roughly 3-4.5 hours of question/review work on first-pass days, including the protected two hours. Additional daytime time is needed but has not been assigned a clock time.

`question_plan.csv` freezes dated counts; builds cannot reshuffle them. The published copy is `question-plan.csv`. Validation checks bank totals, phase deadlines, minimum redo age, buffers and timed practice without double-counting. Keep actual scores, question identifiers and completion logs private. The ASCP 125-question simulation overlaps bank content and is optional repeated practice, not another unique bank.

## Complete Video Plan

- All **17 Blood Bank Guy teaching-library videos**, including the 2024 Last Minute Essentials: 14 hours 1 minute 9 seconds of source runtime. This means every video on the official teaching index checked September 13, not the separate podcast archive.
- All **seven Dr. Margie Morgan pathCast microbiology lectures**: 8 hours 13 minutes 30 seconds. These are 2020-2021 recordings; 2026 companion slide links are included separately.
- All **118 Sketchy Micro lessons**, plus **three Path chemistry lessons** and **three Pharm drug-monitoring lessons**.
- **148 distinct videos / 150 assignments**, with approximately **40 hours 8 minutes** of rounded normal-speed video budgets. Every night is at most 80 video minutes within 90 reserved minutes. No faster playback is assumed.
- The 179-minute Last Minute Essentials has three timestamped assignments: October 13, 00:00-01:00; October 14, 01:00-02:00; October 16, 02:00-02:59. Links start at the assigned timestamp but do not stop automatically.
- October 15 is an explicit catch-up evening, aligned with morning timed practice. October 17-18 stays light. The other **75 previously selected Path/Pharm videos** remain individually linked as optional references; they are not extra nightly quotas.

`video_catalog.tsv` preserves the original 199 Sketchy title/duration/path records without private progress or paid content. `lecture_catalog.json` adds the 24 public lecture records, observed YouTube durations and creator source links. Its validated part boundaries cover the complete long lecture without gaps. `video_plan.json` freezes dated assignments and explicitly lists optional Sketchy lessons. Normal builds cannot reshuffle nights; every required lesson/lecture part must appear exactly once. `scripts/allocate_videos.py` is an initial-allocation utility, refuses overwrite, and provides a reproducible `complete-bbguy` profile for this September 13 revision. Do not rerun it over later actual progress.

Each evening contains individual video URLs and any exact timestamp range. The [complete video library](https://rowlandpettit.com/cp-boards-calendar/#video-library) links all lectures, their assigned dates, source handouts/corrections, Morgan companion slides and optional Sketchy references. Most Blood Bank Guy archive videos are from 2011-2014; consult current guidance when details have changed.

- The question phase sets the default topic: mixed, first-miss review, repeat gaps or light. The earlier `weekly` topic rotation is retained as reference only; it no longer restricts daily question sampling.
- Use a dated `overrides` entry to change one day's `topic`, `note`, `start`, `duration_minutes` or `mode` (`practice`, `timed`, `light`). Edit counts in `question_plan.csv`, not a separate `question_target` override.
- Set `status = "CANCELLED"` on an override to cancel a day while preserving its identity.
- Optional override `goal` or `materials` replaces that day's description section.
- Increment `settings.sequence` and update `settings.updated_at` in UTC for every published plan revision. Keep the namespace and occurrence dates stable.
- Preserve earlier events when updating upcoming work. A weekly-wide change also changes past matching events; prefer dated overrides for mid-plan adjustments.

The daily study block and the existing Lifting calendar are separate. Their overlap is intentional: some study can happen at the gym. This repository never changes gym events. Track actual work rather than treating overlapping reservations as extra hours.

## Local Setup

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make validate
```

Use Python 3.11 or newer. The generator uses `icalendar` for iCalendar serialization and parsing in tests, TOML for the source plan and standard-library XML for RSS. Tests cover all dates, countdowns, floating times, stable UIDs, updates, cancellations, overrides, XML and escaping.

## Privacy

Only scheduling code, generic study objectives and public resource links belong here. Keep paid questions, decks, textbook files, license/registration/payment documents, identifiers and private scores outside the repository. `.local/` and `private-context.md` are git-ignored. A public calendar feed is readable by anyone with its URL; a private repository does not by itself make a Pages site private.

The RSS feed mirrors dated study objectives. Subscribe to the `.ics` URL in Calendar, not the RSS file, and subscribe once rather than importing repeated copies.
