"""Read the frozen, public question quotas; actual progress stays private."""

import csv
from datetime import date, timedelta


COUNTS = ("dojo_new", "ascp_cp_new", "ascp_heme_new", "dojo_first_redo",
          "ascp_first_redo", "repeat_capacity", "timed_questions")


def estimated_misses(count, percent):
    return (count * percent + 99) // 100


def read_question_plan(path, plan):
    settings, config = plan["settings"], plan["question_workload"]
    first_day = settings.get("morning_start_date", settings["start_date"])
    if not 0 <= config["miss_percent"] <= 100:
        raise ValueError("Miss assumption must be a percentage")
    if not (settings["start_date"] <= first_day <= config["first_pass_end"] < config["first_redo_end"]
            < config["light_start"] < settings["exam_date"]):
        raise ValueError("Question phases must be ordered before examination day")
    rows = {}
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != ["date", "phase", *COUNTS]:
            raise ValueError("Unexpected question-plan columns")
        for raw in reader:
            day = date.fromisoformat(raw["date"])
            if day in rows:
                raise ValueError("Duplicate question date")
            row = {key: int(raw[key]) for key in COUNTS}
            if any(value < 0 for value in row.values()):
                raise ValueError("Question counts must be nonnegative")
            phase = ("cancelled" if day < first_day else "first_pass" if day <= config["first_pass_end"] else
                     "first_redo" if day <= config["first_redo_end"] else
                     "repeat" if day < config["light_start"] else "light")
            if raw["phase"] != phase:
                raise ValueError("Question date disagrees with its phase")
            row.update(day=day, phase=phase)
            row["new"] = row["dojo_new"] + row["ascp_cp_new"] + row["ascp_heme_new"]
            row["first_redo"] = row["dojo_first_redo"] + row["ascp_first_redo"]
            if phase == "cancelled" and any(row[key] for key in COUNTS):
                raise ValueError("Cancelled dates cannot retain question quotas")
            if phase != "first_pass" and row["new"]:
                raise ValueError("New questions extend past the first-pass deadline")
            if phase in {"repeat", "light"} and row["first_redo"]:
                raise ValueError("First redos extend past their deadline")
            if phase != "repeat" and row["repeat_capacity"]:
                raise ValueError("Repeat reserve belongs in the buffer phase")
            if row["timed_questions"] not in {0, 55} or row["timed_questions"] > row["repeat_capacity"]:
                raise ValueError("Timed practice must be included in repeat capacity")
            rows[day] = row
    expected = {settings["start_date"] + timedelta(days=i)
                for i in range((settings["exam_date"] - settings["start_date"]).days)}
    if set(rows) != expected:
        raise ValueError("Question plan must cover each study date exactly once")
    for key in ("dojo_new", "ascp_cp_new", "ascp_heme_new", "repeat_capacity"):
        if sum(row[key] for row in rows.values()) != config[key]:
            raise ValueError(f"Question-plan total mismatch: {key}")
    for bank, new_keys in (("dojo", ("dojo_new",)), ("ascp", ("ascp_cp_new", "ascp_heme_new"))):
        total_new = sum(config[key] for key in new_keys)
        if sum(row[f"{bank}_first_redo"] for row in rows.values()) != estimated_misses(total_new, config["miss_percent"]):
            raise ValueError(f"First-redo allowance mismatch: {bank}")
        # A planned redo cannot precede the source questions by less than two days.
        done = 0
        for day, row in sorted(rows.items()):
            available = sum(sum(r[key] for key in new_keys) for d, r in rows.items()
                            if d <= day - timedelta(days=2))
            done += row[f"{bank}_first_redo"]
            if done > estimated_misses(available, config["miss_percent"]):
                raise ValueError(f"Premature or overallocated redos: {bank}")
    return rows


def assignment_label(row):
    if row["phase"] == "cancelled":
        return "Cancelled morning"
    if row["phase"] == "first_pass":
        return f"Mixed | {row['new']} new + {row['first_redo']} redos"
    if row["phase"] == "first_redo":
        return f"Review | {row['first_redo']} first redos"
    if row["phase"] == "repeat":
        return (f"55 timed + {row['repeat_capacity'] - 55} review slots" if row["timed_questions"] else
                f"Repeat gaps | up to {row['repeat_capacity']} questions")
    return "Light final review"


def assignment_notes(row):
    if row["phase"] == "cancelled":
        return "DAILY QUESTION TARGET\n0 questions. This earlier morning was cancelled and its workload reallocated; it is not a catch-up debt."
    if row["phase"] == "light":
        return "DAILY QUESTION TARGET\n0 required new questions or catch-up quotas. Familiar recall only; stop after 20-40 minutes."
    lines = ["DAILY QUESTION TARGET (whole day, not a promise to fit 05:00-07:00)",
             f"PathDojo: {row['dojo_new']} NEW mixed CP/shared questions.",
             f"ASCP: {row['ascp_cp_new']} NEW mixed CP questions plus {row['ascp_heme_new']} NEW shared hematopathology questions.",
             f"First redos: {row['dojo_first_redo']} PathDojo + {row['ascp_first_redo']} ASCP, estimated capacity under the hypothetical 60% miss assumption.",
             f"Total: {row['new']} new + {row['first_redo']} first redos."]
    if row["repeat_capacity"]:
        lines += [f"Repeat/gap reserve: up to {row['repeat_capacity']} questions, not compulsory new work. Use actual repeat misses first, then practical gaps. Stop if queues are clear."]
    if row["timed_questions"]:
        lines += ["Of today's 80 slots, 55 are a timed mixed PathDojo block in 66 minutes and 25 are repeat/gap review. This is repeated-question pacing practice, not a fresh readiness score. Complete explanation review outside the timed block. If first misses remain, clear those instead."]
    if row["new"]:
        lines += ["PathDojo: Tutorial Mode > New (Unanswered) Questions > all CP/shared categories. Select the exact count above.",
                  "ASCP CP: Learning Mode > all CP topics > Random. Shared heme: AP/CP Practice Questions > ONLY AP- Bone Marrow Biopsy and AP- Lymph Node and Spleen > Random. Never select all AP topics.",
                  "ASCP counts must represent unique completed questions. Check history/available filters and maintain a private seen-question ledger; repeated random draws do not count as new."]
    if row["first_redo"]:
        lines += ["Redo closed-book from your dated miss ledger, preferably questions at least two days old. PathDojo's Questions Incorrect Last Time Taken is a candidate pool, not proof of date or first-redo status. Questions Incorrect Ever also includes previously corrected misses. In both banks, use history/ledger to avoid redoing the same entries instead of clearing the queue.",
                  "The ASCP redo count combines CP and shared heme. Use actual misses, not a fixed invented split. If fewer misses exist, use leftover capacity for uncertain answers or rest; if more exist, update upcoming quotas."]
    return "\n".join(lines)
