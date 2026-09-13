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

Edit `plan.toml`, then run `make validate`, commit and push to `main`. GitHub Actions regenerates the public feeds and deploys GitHub Pages. Calendar subscribers receive updates on their configured refresh schedule; updates are not instantaneous.

`video_catalog.tsv` contains the 199 selected lesson titles, rounded durations and directly observed URL paths, with no private progress or paid content. `video_plan.json` freezes the dated lesson assignments so normal builds cannot reshuffle completed nights. Edit upcoming assignments explicitly and keep every selected lesson assigned exactly once. `scripts/allocate_videos.py` is only an initial-allocation utility and refuses to overwrite an existing file. Each evening event includes its individual video URLs, and the corresponding web section provides clickable lesson links.

- Change `weekly` for the default topic rotation.
- Use a dated `overrides` entry to change one day's `topic`, `note`, `start`, `duration_minutes`, `question_target` or `mode` (`practice`, `timed`, `light`).
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
