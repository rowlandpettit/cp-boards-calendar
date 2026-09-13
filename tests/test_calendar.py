from copy import deepcopy
import csv
from datetime import date, timedelta
import json
from pathlib import Path
import sys
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from icalendar import Calendar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_calendar import build_calendar, build_rss, build_sessions, build_video_sessions, generate, read_plan, read_video_catalog, write_pages
from question_workload import read_question_plan, estimated_misses


class StudyCalendarTests(unittest.TestCase):
    def setUp(self):
        self.plan = read_plan(ROOT / "plan.toml")

    def events(self, plan=None):
        plan = plan or self.plan
        return Calendar.from_ical(build_calendar(plan, build_sessions(plan))).walk("VEVENT")

    def test_every_day_and_exact_countdowns(self):
        events = self.events()
        self.assertEqual(len(events), 35)
        self.assertEqual(len({str(e["UID"]) for e in events}), 35)
        for index, event in enumerate(events):
            expected = date(2026, 9, 14) + timedelta(days=index)
            start, end = event.decoded("DTSTART"), event.decoded("DTEND")
            self.assertEqual(start.date(), expected)
            self.assertEqual((start.hour, start.minute), (5, 0))
            self.assertEqual((end.hour, end.minute), (7, 0))
            self.assertIsNone(start.tzinfo)
            self.assertNotIn("RRULE", event)
            left = (date(2026, 10, 19) - expected).days
            self.assertIn(f"{left} {'day' if left == 1 else 'days'} left", str(event["SUMMARY"]))
            self.assertEqual(event.decoded("DTSTAMP").utcoffset(), timedelta(0))
            self.assertTrue(str(event["ATTACH"]).endswith("/context.html"))
            self.assertIn("MATERIALS", str(event["DESCRIPTION"]))
            self.assertIn("FLEXIBLE PLAN", str(event["DESCRIPTION"]))
        self.assertIn("54 new + 0 redos", str(events[0]["SUMMARY"]))
        self.assertIn("1 day left", str(events[-1]["SUMMARY"]))

    def test_topic_time_and_revision_edits_keep_uids(self):
        before = self.events()
        changed = deepcopy(self.plan)
        changed["settings"]["sequence"] += 1
        changed["settings"]["updated_at"] += timedelta(hours=1)
        changed["overrides"]["2026-09-15"] = {"topic": "micro", "start": "05:30", "duration_minutes": 90}
        after = self.events(changed)
        self.assertEqual([e["UID"] for e in before], [e["UID"] for e in after])
        self.assertIn("Microbiology", str(after[1]["SUMMARY"]))
        self.assertEqual(after[1].decoded("DTEND").hour, 7)
        self.assertEqual(int(after[1]["SEQUENCE"]), self.plan["settings"]["sequence"] + 1)

    def test_cancel_preserves_occurrence(self):
        self.plan["overrides"]["2026-09-15"] = {"status": "CANCELLED"}
        events = self.events()
        self.assertEqual(len(events), 35)
        self.assertEqual(str(events[1]["STATUS"]), "CANCELLED")

    def test_escaping_and_utf8_round_trip(self):
        value = "Panel, QC; A\\B\nInterpretation <test> & café"
        self.plan["overrides"]["2026-09-14"]["note"] = value
        payload = build_calendar(self.plan, build_sessions(self.plan))
        self.assertIn(value, str(Calendar.from_ical(payload).walk("VEVENT")[0]["DESCRIPTION"]))
        self.assertTrue(all(len(line) <= 75 for line in payload.split(b"\r\n")))

    def test_rss_has_stable_guid_and_context(self):
        sessions = build_sessions(self.plan)
        root = ET.fromstring(build_rss(self.plan, sessions))
        items = root.findall("./channel/item")
        self.assertEqual(len(items), 35)
        self.assertEqual([item.findtext("guid") for item in items], [s["uid"] for s in sessions])
        self.assertIn("5-7 AM", items[0].findtext("description"))

    def test_invalid_configuration_fails(self):
        mutations = [
            lambda p: p["settings"].update(exam_date=date(2026, 9, 14)),
            lambda p: p["overrides"].update({"2026-10-19": {"topic": "micro"}}),
            lambda p: p["overrides"].update({"2026-09-15": {"mode": "unknown"}}),
            lambda p: p["overrides"].update({"2026-09-15": {"topic": "unknown"}}),
            lambda p: p["settings"].update(updated_at=p["settings"]["updated_at"].replace(tzinfo=None)),
            lambda p: p["resources"].update(dojo="https://user:secret@example.org/"),
        ]
        for mutate in mutations:
            plan = deepcopy(self.plan)
            mutate(plan)
            with self.assertRaises(ValueError):
                build_sessions(plan)

    def test_generation_is_deterministic(self):
        sessions = build_sessions(self.plan)
        self.assertEqual(build_calendar(self.plan, sessions), build_calendar(self.plan, sessions))

    def test_complete_generation_and_safe_html(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy(ROOT / "plan.toml", root)
            shutil.copy(ROOT / "video_plan.json", root)
            shutil.copy(ROOT / "video_catalog.tsv", root)
            shutil.copy(ROOT / "question_plan.csv", root)
            shutil.copytree(ROOT / "templates", root / "templates")
            generate(root)
            public = root / "public"
            self.assertEqual(len(Calendar.from_ical((public / "cp-study.ics").read_bytes()).walk("VEVENT")), 69)
            text = (public / "index.html").read_text()
            self.assertNotIn("@@", text)
            self.assertIn("05:00-07:00", text)
            self.assertIn('id="study-2026-09-15"', text)
            self.assertIn('id="video-2026-09-15"', text)
            self.assertIn('ASCP shared heme setup</a>', text)
            self.assertIn('href="https://pathdojo.com/exams/create/?exam_type=tutorial"', text)
            self.assertEqual((public / "question-plan.csv").read_bytes(), (root / "question_plan.csv").read_bytes())
            self.assertIn('href="https://app.sketchy.com/study/medical/chapter/gram-positive-cocci/lesson/staphylococcus-aureus"', text)
            self.plan["overrides"]["2026-09-14"]["goal"] = "<script>not executable</script>"
            write_pages(self.plan, build_sessions(self.plan), public, root)
            self.assertIn("&lt;script&gt;not executable&lt;/script&gt;", (public / "index.html").read_text())

    def test_catalog_matches_browser_inventory(self):
        catalog = read_video_catalog(ROOT / "video_catalog.tsv")
        rows = sorted("\t".join(str(v[k]) for k in ("course", "minutes", "title", "path")) for v in catalog.values())
        observed = "\n".join(rows)
        fingerprint = 2166136261
        for char in observed:
            fingerprint = ((fingerprint ^ ord(char)) * 16777619) & 0xffffffff
        # Snapshot of the 199 selected visible lesson rows on 2026-09-13, excluding progress.
        self.assertEqual(len(observed), 20404)
        self.assertEqual(fingerprint, 2846960811)
        for course, count, minutes in (("Micro", 118, 948), ("Path", 43, 847), ("Pharm", 38, 493)):
            subset = [v for v in catalog.values() if v["course"] == course]
            self.assertEqual(len(subset), count)
            self.assertEqual(sum(v["minutes"] for v in subset), minutes)

    def test_evening_dates_runtime_links_and_stable_identity(self):
        catalog = read_video_catalog(ROOT / "video_catalog.tsv")
        allocation = json.loads((ROOT / "video_plan.json").read_text())
        sessions = build_video_sessions(self.plan, allocation, catalog)
        self.assertEqual(len(sessions), 34)
        self.assertEqual(sum(s["video_minutes"] for s in sessions), 2288)
        self.assertEqual(sum(len(s["videos"]) for s in sessions), 199)
        for index, session in enumerate(sessions):
            self.assertEqual(session["day"], date(2026, 9, 15) + timedelta(days=index))
            self.assertEqual(session["start"].strftime("%H:%M"), "21:00")
            self.assertEqual(session["end"].strftime("%H:%M"), "22:30")
            self.assertLessEqual(session["video_minutes"], 80)
            self.assertIsNone(session["start"].tzinfo)
            self.assertEqual(session["left"], (self.plan["settings"]["exam_date"] - session["day"]).days)
            for video in session["videos"]:
                self.assertIn(video["url"], session["description"])
            if session["day"] >= date(2026, 10, 17):
                self.assertEqual(session["mode"], "light")
                self.assertFalse(session["videos"])
        morning = build_sessions(self.plan)
        combined = sorted(morning + sessions, key=lambda s: s["start"])
        self.assertEqual(len({s["uid"] for s in combined}), 69)
        self.assertEqual(len({s["anchor"] for s in combined}), 69)
        events = Calendar.from_ical(build_calendar(self.plan, combined)).walk("VEVENT")
        self.assertEqual({str(e["UID"]) for e in events if str(e["UID"]).startswith("study-")}, {s["uid"] for s in morning})
        self.assertEqual(len(ET.fromstring(build_rss(self.plan, combined)).findall("./channel/item")), 69)
        changed = deepcopy(allocation)
        changed["start"] = "20:30"
        self.assertEqual([s["uid"] for s in sessions], [s["uid"] for s in build_video_sessions(self.plan, changed, catalog)])

    def test_invalid_video_assignments_fail(self):
        catalog = read_video_catalog(ROOT / "video_catalog.tsv")
        allocation = json.loads((ROOT / "video_plan.json").read_text())
        mutations = [
            lambda a: a["sessions"][0].update(date="2026-10-19"),
            lambda a: a["sessions"][0]["lessons"].append(a["sessions"][0]["lessons"][0]),
            lambda a: a["sessions"][0]["lessons"].append("missing/lesson/missing"),
            lambda a: a["sessions"][0]["lessons"].pop(),
            lambda a: a.update(max_video_minutes=10),
            lambda a: a.update(start="23:30"),
        ]
        for mutate in mutations:
            changed = deepcopy(allocation)
            mutate(changed)
            with self.assertRaises(ValueError):
                build_video_sessions(self.plan, changed, catalog)

    def test_two_bank_totals_and_phase_deadlines(self):
        rows = read_question_plan(ROOT / "question_plan.csv", self.plan)
        expected = {"dojo_new": 885, "ascp_cp_new": 157, "ascp_heme_new": 54,
                    "dojo_first_redo": 531, "ascp_first_redo": 127,
                    "repeat_capacity": 320, "timed_questions": 55}
        for key, total in expected.items():
            self.assertEqual(sum(r[key] for r in rows.values()), total)
        self.assertEqual(sum(r["new"] for r in rows.values()), 1096)
        self.assertEqual(sum(r["first_redo"] for r in rows.values()), 658)
        self.assertEqual(estimated_misses(658, 60), 395)
        self.assertEqual(395 - expected["repeat_capacity"], 75)
        self.assertEqual(rows[date(2026, 9, 14)]["new"], 54)
        self.assertEqual(rows[date(2026, 9, 15)]["new"], 53)
        self.assertEqual(rows[date(2026, 9, 16)]["first_redo"], 10)
        self.assertEqual(rows[date(2026, 10, 4)]["new"], 52)
        early = [r for d, r in rows.items() if d <= date(2026, 10, 4)]
        self.assertEqual(sum(r["first_redo"] for r in early), 190)
        for day, row in rows.items():
            if day > date(2026, 10, 4):
                self.assertEqual(row["new"], 0)
            if day > date(2026, 10, 12):
                self.assertEqual(row["first_redo"], 0)
            if day >= date(2026, 10, 17):
                self.assertEqual(row["repeat_capacity"], 0)

    def test_daily_quotas_in_feed_and_matching_site(self):
        sessions = build_sessions(self.plan)
        first = sessions[0]
        for text in ("PathDojo: 43 NEW", "ASCP: 8 NEW", "3 NEW shared", "54 new + 0 first redos",
                     "05:25-06:40", "06:40-06:55", "additional daytime study"):
            self.assertIn(text, first["description"])
        self.assertEqual(first["assignment"]["new"], 54)
        self.assertIn("hypothetical 60%", sessions[2]["description"])
        self.assertEqual(sessions[31]["assignment"]["timed_questions"], 55)
        self.assertEqual(sessions[31]["assignment"]["repeat_capacity"], 80)
        self.assertIn("55 timed + 25 review slots", sessions[31]["title"])
        self.assertIn("0 required new", sessions[-1]["description"])
        self.assertNotIn("Targeted reading for today's topic", first["description"])

    def test_invalid_question_plans_fail(self):
        with (ROOT / "question_plan.csv").open(newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        mutations = [
            lambda r: r[0].update(dojo_new="44"),
            lambda r: r[0].update(date="2026-09-15"),
            lambda r: r.pop(),
            lambda r: r[0].update(ascp_cp_new="-1"),
            lambda r: r[21].update(phase="first_pass"),
            lambda r: r[31].update(timed_questions="125"),
            lambda r: (r[0].update(dojo_first_redo="8"), r[2].update(dojo_first_redo="0")),
            lambda r: (r[20].update(dojo_new="0"), r[21].update(dojo_new="42")),
            lambda r: (r[29].update(repeat_capacity="0"), r[34].update(repeat_capacity="80")),
        ]
        for mutate in mutations:
            changed = deepcopy(rows)
            mutate(changed)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "questions.csv"
                with path.open("w", newline="") as stream:
                    writer = csv.DictWriter(stream, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(changed)
                with self.assertRaises(ValueError):
                    read_question_plan(path, self.plan)

    def test_conflicting_legacy_target_fails(self):
        self.plan["overrides"]["2026-09-14"]["question_target"] = 25
        with self.assertRaises(ValueError):
            build_sessions(self.plan)


if __name__ == "__main__":
    unittest.main()
