# Maintaining This Calendar

- Read `README.md`, `context.md` and `plan.toml` before changing the schedule.
- Scope is CP-only ABPath certification, not AP boards or Step/USMLE. Prioritize CP questions and explanation review, delayed redos, practical laboratory interpretation and selected recall. Sketchy Path/Pharm are optional foundation support, not the governing syllabus. Do not expand full courses or require reading every page simply because the resources are available.
- This repository is only the publishable CP study calendar. Never add paid materials, actual scores, licensing, payments, identifiers or unrelated personal data.
- The original materials and detailed audits live outside this repo. Local continuity information may be in ignored `private-context.md`.
- Preserve each study occurrence's date-based UID. For cancellation, retain the event with `status = "CANCELLED"`; do not remove it silently.
- Change upcoming dated overrides for adaptive planning. Do not rewrite historical topics without explicit intent.
- Increment the sequence and UTC update timestamp for published changes; keep event dates and namespace stable.
- Run `make validate` before a commit. Push only the intended calendar changes. Do not revert unrelated edits.
- Verify the deployed HTTPS feed and the user's subscribed calendar separately. A successful push does not establish a Calendar refresh.
- Do not move or alter the separate workout calendar unless explicitly authorized.
