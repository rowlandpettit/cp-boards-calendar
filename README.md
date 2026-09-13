# CP Boards Calendar

Daily protected study blocks for the CP-only examination on October 19, 2026.

## Calendar

- [Study calendar](https://rowlandpettit.com/cp-boards-calendar/)
- [Subscribe in Apple Calendar](webcal://rowlandpettit.com/cp-boards-calendar/cp-study.ics)
- [HTTPS calendar feed](https://rowlandpettit.com/cp-boards-calendar/cp-study.ics)
- [RSS feed](https://rowlandpettit.com/cp-boards-calendar/rss.xml), for RSS readers rather than Calendar

The 35 morning blocks run September 14-October 18, 5:00-7:00 AM as floating local times. Another 34 separate Sketchy blocks run September 15-October 18, 9:00-10:30 PM, in the same subscription. The final two evenings are optional light recall. Each occurrence has a stable date-based ID and countdown to October 19; no event is generated on examination day.

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

`video_catalog.tsv` contains the 199 selected lesson titles, rounded durations and directly observed URL paths, with no private progress or paid content. `video_plan.json` freezes the dated lesson assignments so normal builds cannot reshuffle completed nights. Edit upcoming assignments explicitly and keep every selected lesson assigned exactly once. `scripts/allocate_videos.py` is only an initial-allocation utility and refuses to overwrite an existing file. Each evening event includes its individual video URLs, and the corresponding web section provides clickable lesson links.

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
