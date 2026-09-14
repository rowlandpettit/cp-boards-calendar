# CP Boards Calendar

Daily protected study blocks for the CP-only examination on October 19, 2026.

## Calendar

- [Study calendar](https://rowlandpettit.com/cp-boards-calendar/)
- [Subscribe in Apple Calendar](webcal://rowlandpettit.com/cp-boards-calendar/cp-study.ics)
- [HTTPS calendar feed](https://rowlandpettit.com/cp-boards-calendar/cp-study.ics)
- [RSS feed](https://rowlandpettit.com/cp-boards-calendar/rss.xml), for RSS readers rather than Calendar

The revised 31 morning blocks start Friday September 18 and run through October 18, 5:00-7:00 AM as floating local times. Friday is the kickoff; a longer morning was requested, but its end time is still pending, so no extra hours have been reserved. Another 33 video blocks begin Wednesday September 16, 9:00-10:30 PM. Thursday September 17 has exactly five review videos (about 54 minutes). The final two evenings stay light. The calendar, RSS and website contain 64 active occurrences. At the user's explicit request, the five former September 14-17 morning and September 15 evening cancellation records are omitted entirely. All remaining occurrence IDs and assignments are unchanged; no event is generated on exam day.

Event notes include the objective, a realistic two-hour routine, selected materials, resource links and the adaptation policy. The main aim is learning from questions and recurring gaps, not completing every bank and deck. [Study strategy](context.md).

## Edit and Sync

Edit `plan.toml` and the dated quotas in `question_plan.csv`, then run `make validate`, commit and push to `main`. GitHub Actions regenerates the public feeds and deploys GitHub Pages. Calendar subscribers receive updates on their configured refresh schedule; updates are not instantaneous.

## Two-Bank Workload

- Required first pass: 885 PathDojo + 157 ASCP CP + 54 ASCP shared hematopathology = **1,096 unique questions**, September 18-October 4, 17 days.
- September 18-25: 65 new daily. September 26-October 4: 64 new daily. Friday kickoff is 53 PathDojo + 9 ASCP CP + 3 shared heme, with no first redos yet. Each date lists its exact split.
- September 20-October 4: 8 PathDojo + 2 ASCP first redos daily, 150 total. These are estimated slots, not actual results. No redos are due before September 20.
- October 5-12: clear the other 508 estimated first redos, 63-64 daily. Under the hypothetical 60% incorrect assumption, first-redo capacity still totals **658** (531 PathDojo, 127 ASCP).
- October 13-16: **320 additional repeat/gap slots**, up to 80 daily. October 15 includes a 55-question timed block within its 80 slots, not in addition. October 17-18 remains light.
- The morning prioritizes questions and explanations, with 15 minutes of targeted reading. Daily quotas are whole-day targets: expect roughly 4-5.25 hours of question/review work on first-pass days, including the protected two hours. About 2-3.25 additional daytime hours are needed but have not been assigned a clock time. Calibrate September 20.

`question_plan.csv` freezes dated counts; builds cannot reshuffle them. The published copy is `question-plan.csv`. Validation checks bank totals, phase deadlines, minimum redo age, buffers and timed practice without double-counting. Keep actual scores, question identifiers and completion logs private. The ASCP 125-question simulation overlaps bank content and is optional repeated practice, not another unique bank.

## Complete Video Plan

- All **17 Blood Bank Guy teaching-library videos**, including the 2024 Last Minute Essentials: 14 hours 1 minute 9 seconds of source runtime. This means every video on the official teaching index checked September 13, not the separate podcast archive.
- All **seven Dr. Margie Morgan pathCast microbiology lectures**: 8 hours 13 minutes 30 seconds. These are 2020-2021 recordings; 2026 companion slide links are included separately.
- All **118 Sketchy Micro lessons**, plus **three Path chemistry lessons** and **three Pharm drug-monitoring lessons**.
- **148 distinct videos / 150 assignments**, with approximately **40 hours 8 minutes** of rounded normal-speed video budgets. Every night is at most 80 video minutes within 90 reserved minutes. No faster playback is assumed.
- The 179-minute Last Minute Essentials has three timestamped assignments: October 13, 00:00-01:00; October 14, 01:00-02:00; October 16, 02:00-02:59. Links start at the assigned timestamp but do not stop automatically.
- Starting a night later uses the former October 15 video catch-up evening for assigned videos; the morning timed block and all question-review reserves are unchanged. October 17-18 stays light. The other **75 previously selected Path/Pharm videos** remain individually linked as optional references; they are not extra nightly quotas.
- Thursday September 17's five videos are Acquired B, RhIG Dosage, Why Leukoreduce, Why Irradiate, and Sketchy Staphylococcus aureus. They are included once in the complete inventory, not extra assignments or assumed completed work.

`video_catalog.tsv` preserves the original 199 Sketchy title/duration/path records without private progress or paid content. `lecture_catalog.json` adds the 24 public lecture records, observed YouTube durations and creator source links. Its validated part boundaries cover the complete long lecture without gaps. `video_plan.json` freezes dated assignments and explicitly lists optional Sketchy lessons. Normal builds cannot reshuffle nights; every required lesson/lecture part must appear exactly once. `scripts/allocate_videos.py` is an initial-allocation utility, refuses overwrite, and provides a reproducible `wednesday-kickoff` profile for the September 14 revision. Earlier profiles are historical. Do not rerun over later actual progress.

Each evening contains individual video URLs and any exact timestamp range. The [complete video library](https://rowlandpettit.com/cp-boards-calendar/#video-library) links all lectures, their assigned dates, source handouts/corrections, Morgan companion slides and optional Sketchy references. Most Blood Bank Guy archive videos are from 2011-2014; consult current guidance when details have changed.

- The question phase sets the default topic: mixed, first-miss review, repeat gaps or light. The earlier `weekly` topic rotation is retained as reference only; it no longer restricts daily question sampling.
- Use a dated `overrides` entry to change one day's `topic`, `note`, `start`, `duration_minutes` or `mode` (`practice`, `timed`, `light`). Edit counts in `question_plan.csv`, not a separate `question_target` override.
- Set `status = "CANCELLED"` on an override to cancel a day while preserving its identity.
- When the user explicitly asks to remove a cancelled block entirely, add its date-based anchor to `settings.removed_occurrences`. The generator omits it from Calendar, RSS and the website, while preserving the source history. Only known cancelled occurrences may be removed this way. Do not add a duplicate calendar subscription.
- The original `start_date` remains the source history boundary. `morning_start_date` controls the active question launch; earlier CSV rows have phase `cancelled` and zero quotas. Cancellation records not explicitly removed remain transparent and shown separately on the website. Video cancellations use kind `cancelled`, no lessons, and the original date-based UID.
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
