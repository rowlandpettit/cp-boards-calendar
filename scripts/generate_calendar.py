#!/usr/bin/env python3
"""Generate a dated study calendar and RSS feed from the editable TOML plan."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
from email.utils import format_datetime
import html
import json
from math import ceil
from pathlib import Path
import re
import tomllib
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from icalendar import Calendar, Event
from question_workload import assignment_label, assignment_notes, read_question_plan


ROOT = Path(__file__).resolve().parents[1]
DAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
MODES = {"practice", "timed", "light"}
SKETCHY_BASE = "https://app.sketchy.com/study/medical/chapter/"


def read_plan(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def validate_plan(plan: dict) -> None:
    settings = plan["settings"]
    if not isinstance(settings["start_date"], date) or not isinstance(settings["exam_date"], date):
        raise ValueError("Start and exam dates must be TOML dates")
    if not 0 < (settings["exam_date"] - settings["start_date"]).days <= 366:
        raise ValueError("Study range must end before the exam and span at most one year")
    if not settings["floating_times"]:
        raise ValueError("This feed uses floating local times, like the workout feed")
    if settings["sequence"] < 0:
        raise ValueError("Sequence must be nonnegative")
    updated = settings["updated_at"]
    if not isinstance(updated, datetime) or updated.utcoffset() != timedelta(0):
        raise ValueError("updated_at must be a UTC TOML datetime")
    for value in (settings["site_url"], settings["repository_url"], *plan["resources"].values()):
        url = urlparse(value)
        if url.scheme != "https" or not url.netloc or url.username or url.password:
            raise ValueError("Published links must be credential-free HTTPS URLs")
    if set(plan["weekly"]) != set(DAYS):
        raise ValueError("Weekly plan must include every day")
    for key in plan.get("overrides", {}):
        day = date.fromisoformat(key)
        if not settings["start_date"] <= day < settings["exam_date"]:
            raise ValueError(f"Override {key} is outside the study range")


def routine(mode: str, start: datetime, duration: int, target: int, phase: str = "first_pass") -> str:
    if mode == "light":
        return "Light session: 20-40 minutes of familiar recall and logistics. The remaining reserved time is optional. No new broad material."
    if duration != 120:
        return f"Adapt this {duration}-minute session: questions, priority explanations, selected recall, then a brief progress log. Reduce the {target}-question target if needed."
    steps = (
        [(0, 66, "55-question timed mixed block"), (66, 110, "Review priority misses and uncertain answers"), (110, 120, "List unresolved explanations and log actual work")]
        if mode == "timed"
        else [(0, 100, "Closed-book missed-question review and explanations; work toward today's daily queue target"), (100, 115, "Targeted guide reading, figures or calculations for recurring gaps"), (115, 120, "Log unique redos, repeat misses and remaining daytime work")]
        if phase in {"first_redo", "repeat"}
        else [(0, 25, "Due first-redo quota and explanations; if none are due, start new mixed questions"), (25, 100, "New mixed PathDojo and ASCP questions with explanations"), (100, 115, "Targeted guide reading for misses; do not read the entire book first"), (115, 120, "Log unique new questions, first redos, repeat misses and daytime remainder")]
    )
    return "\n".join(
        f"{(start + timedelta(minutes=a)):%H:%M}-{(start + timedelta(minutes=b)):%H:%M}: {label}"
        for a, b, label in steps
    ) + "\nFinish the remaining daily quota in additional daytime study. That time is required if work remains, but no unapproved extra calendar slot has been added. Anki is distributed through the day."


def build_sessions(plan: dict, questions: dict | None = None) -> list[dict]:
    validate_plan(plan)
    if questions is None:
        questions = read_question_plan(ROOT / "question_plan.csv", plan)
    settings, strategy = plan["settings"], plan["strategy"]
    sessions = []
    day = settings["start_date"]
    while day < settings["exam_date"]:
        override = plan.get("overrides", {}).get(day.isoformat(), {})
        assignment = questions[day]
        default_topic = {"first_pass": "mixed", "first_redo": "redo", "repeat": "consolidate", "light": "light"}[assignment["phase"]]
        topic_id = override.get("topic", default_topic)
        if topic_id not in plan["topics"]:
            raise ValueError(f"Unknown topic: {topic_id}")
        topic = plan["topics"][topic_id]
        mode = override.get("mode", "light" if assignment["phase"] == "light" else "timed" if assignment["timed_questions"] else "practice")
        if mode not in MODES:
            raise ValueError(f"Unknown mode: {mode}")
        status = override.get("status", "CONFIRMED")
        if status not in {"CONFIRMED", "CANCELLED", "TENTATIVE"}:
            raise ValueError(f"Unknown status: {status}")
        local_time = time.fromisoformat(override.get("start", settings["start"]))
        if local_time.tzinfo is not None:
            raise ValueError("Study start must be a floating time")
        start = datetime.combine(day, local_time)
        duration = int(override.get("duration_minutes", settings["duration_minutes"]))
        if not 0 < duration <= 720:
            raise ValueError("Invalid session duration")
        end = start + timedelta(minutes=duration)
        if end.date() != day:
            raise ValueError("Study blocks must remain on their occurrence date")
        left = (settings["exam_date"] - day).days
        countdown = f"{left} {'day' if left == 1 else 'days'} left"
        title = f"CP Boards | {countdown} | {assignment_label(assignment)}"
        if topic_id != default_topic and topic_id != "timed":
            title += " | " + topic["title"]
        target = assignment["new"] + assignment["first_redo"] + assignment["repeat_capacity"]
        if "question_target" in override and override["question_target"] != target:
            raise ValueError("Edit dated question_plan.csv quotas instead of a conflicting question_target")
        if target < 0:
            raise ValueError("Question target must be nonnegative")
        goal = override.get("goal", topic["goal"])
        materials = override.get("materials", topic["materials"])
        context_url = settings["site_url"].rstrip("/") + "/context.html"
        url = settings["site_url"].rstrip("/") + "/#study-" + day.isoformat()
        resource_keys = list(dict.fromkeys(["dojo", "ascp_cp", "ascp_heme", *topic["links"]]))
        resource_text = "\n".join(f"{key}: {plan['resources'][key]}" for key in resource_keys)
        question_links = [(label, plan["resources"][key]) for key, label in (
            ("dojo", "PathDojo mixed setup"), ("ascp_cp", "ASCP CP setup"), ("ascp_heme", "ASCP shared heme setup"))]
        description = "\n\n".join(filter(None, [
            f"{countdown.capitalize()} until the CP exam on {settings['exam_date']:%B %d, %Y}. Countdown is from this study date.",
            assignment_notes(assignment), strategy["objective"], "TODAY\n" + goal,
            "SESSION\n" + routine(mode, start, duration, target, assignment["phase"]),
            strategy["review_rule"], strategy["anki_rule"],
            "MATERIALS\n" + materials, override.get("note", ""),
            "FLEXIBLE PLAN\n" + strategy["flexibility"] + " " + strategy["capacity"],
            strategy["gym"], "RESOURCE LINKS\n" + resource_text,
            "Study context: " + context_url,
            "Exact dated question quotas: " + settings["site_url"].rstrip("/") + "/question-plan.csv",
            "Editable plan: " + settings["repository_url"] + "/blob/main/plan.toml",
        ]))
        sessions.append(dict(day=day, start=start, end=end, left=left, title=title,
                             goal=goal, materials=materials, description=description,
                             status=status, mode=mode, url=url, context_url=context_url,
                             anchor=f"study-{day.isoformat()}",
                             assignment=assignment, question_links=question_links,
                             uid=f"study-{day.isoformat()}@{settings['namespace']}"))
        day += timedelta(days=1)
    return sessions


def read_video_catalog(path: Path) -> dict:
    catalog = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            key = row["path"]
            if key in catalog or not key or any(c in key for c in "?#:@") or ".." in key:
                raise ValueError("Duplicate or unsafe lesson path")
            if len(key.split("/")) != 3 or key.split("/")[1] != "lesson":
                raise ValueError("Expected a directly observed Sketchy chapter/lesson path")
            row["minutes"] = int(row["minutes"])
            if row["course"] not in {"Micro", "Path", "Pharm"} or not 0 < row["minutes"] <= 80:
                raise ValueError("Invalid lesson metadata")
            row["url"] = SKETCHY_BASE + key
            catalog[key] = row
    return catalog


def timestamp(seconds: int) -> str:
    hours, remaining = divmod(seconds, 3600)
    minutes, seconds = divmod(remaining, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def read_lecture_catalog(path: Path) -> dict:
    catalog, seen = {}, set()
    for video in json.loads(path.read_text())["videos"]:
        key = video["id"]
        if not re.fullmatch(r"(?:bbguy|morgan)-[a-z0-9]+", key) or key in seen:
            raise ValueError("Invalid or duplicate lecture ID")
        seen.add(key)
        if video["course"] not in {"Blood Bank Guy", "Morgan"} or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video["youtube_id"]):
            raise ValueError("Invalid lecture provider or YouTube ID")
        source = urlparse(video["source_url"])
        if source.scheme != "https" or source.netloc not in {"www.bbguy.org", "www.microbeswithmorgan.com"}:
            raise ValueError("Invalid lecture source")
        seconds = video["seconds"]
        boundaries = video.get("part_ends", [seconds])
        if type(seconds) is not int or seconds <= 0 or not boundaries or boundaries[-1] != seconds:
            raise ValueError("Lecture parts must cover the full runtime")
        start = 0
        for index, end in enumerate(boundaries, 1):
            if type(end) is not int or not start < end <= seconds or end - start > 80 * 60:
                raise ValueError("Invalid lecture segment")
            part_key = key if len(boundaries) == 1 else f"{key}-part{index}"
            title = video["title"]
            url = "https://www.youtube.com/watch?v=" + video["youtube_id"]
            if len(boundaries) > 1:
                title += f" | Part {index}/{len(boundaries)}: {timestamp(start)}-{timestamp(end)}"
                url += f"&t={start}s"
            catalog[part_key] = dict(video, path=part_key, title=title, url=url,
                                     minutes=ceil((end - start) / 60), start_seconds=start, end_seconds=end)
            start = end
    return catalog


def read_all_videos(root: Path = ROOT) -> dict:
    return read_video_catalog(root / "video_catalog.tsv") | read_lecture_catalog(root / "lecture_catalog.json")


def build_video_sessions(plan: dict, allocation: dict, catalog: dict) -> list[dict]:
    settings = plan["settings"]
    start_time = time.fromisoformat(allocation["start"])
    duration = int(allocation["duration_minutes"])
    limit = int(allocation["max_video_minutes"])
    if start_time.tzinfo or not 0 < limit <= duration - 10 or duration > 180:
        raise ValueError("Videos must leave at least ten minutes for recall")
    optional_list = allocation.get("optional_lessons", [])
    optional = set(optional_list)
    if len(optional) != len(optional_list) or any(key not in catalog or catalog[key]["course"] not in {"Path", "Pharm"} for key in optional):
        raise ValueError("Only selected Sketchy Path/Pharm can be moved to optional")
    result, seen_dates, seen_lessons, lecture_positions = [], set(), set(), {}
    for item in sorted(allocation["sessions"], key=lambda item: item["date"]):
        day = date.fromisoformat(item["date"])
        if day in seen_dates or not settings["start_date"] <= day < settings["exam_date"]:
            raise ValueError("Duplicate or out-of-range video date")
        seen_dates.add(day)
        kind = item["kind"]
        if kind not in {"watch", "review", "light"} or (kind == "watch") != bool(item["lessons"]):
            raise ValueError("Invalid video session kind")
        videos = []
        for key in item["lessons"]:
            if key in seen_lessons or key not in catalog or key in optional:
                raise ValueError("Duplicate or unknown assigned lesson")
            video = catalog[key]
            if "id" in video:
                if video["start_seconds"] != lecture_positions.get(video["id"], 0):
                    raise ValueError("Lecture parts must be watched in order without gaps")
                lecture_positions[video["id"]] = video["end_seconds"]
            seen_lessons.add(key)
            videos.append(catalog[key])
        minutes = sum(v["minutes"] for v in videos)
        if minutes > limit:
            raise ValueError("Video runtime exceeds the nightly budget")
        start = datetime.combine(day, start_time)
        end = start + timedelta(minutes=duration)
        if start.date() != end.date():
            raise ValueError("Video block crosses midnight")
        left = (settings["exam_date"] - day).days
        countdown = f"{left} {'day' if left == 1 else 'days'} left"
        providers = list(dict.fromkeys(v["course"] if v["course"] in {"Blood Bank Guy", "Morgan"} else "Sketchy" for v in videos))
        topic = (" + ".join(providers) + f" | {len(videos)} videos/parts" if videos else "Videos | Light recall" if kind == "light" else "Videos | Catch-up + recall")
        anchor = f"video-{day.isoformat()}"
        base = settings["site_url"].rstrip("/")
        goal = ("Watch every listed video or exact timestamp range. Rewatch Sketchy even if previously marked completed. Pause to interpret panels or images before the answer; explain a diagnostic distinction after each. Timestamp links set the start only: stop at the listed end."
                if videos else "No new lessons. Optional 15-20 minutes of familiar recall, then stop early and protect rest."
                if kind == "light" else "Use this buffer for unfinished assigned lessons or recurring weak concepts. Do not add a new course.")
        links = "\n\n".join(f"{i}. [{v['course']}] {v['title']} (~{v['minutes']} min)\n{v['url']}"
                              for i, v in enumerate(videos, 1))
        notes = [f"{countdown.capitalize()} until the CP exam on {settings['exam_date']:%B %d, %Y}.",
                 "TODAY\n" + goal,
                 f"SESSION\n{start:%H:%M}-{end:%H:%M} reserved. Approximately {minutes} minutes of video at normal speed; {duration - minutes} minutes remain for pauses, recall and a brief log. Displayed durations are rounded, not second-exact." if videos else f"SESSION\n{start:%H:%M}-{end:%H:%M} reserved; unused time is optional.",
                 "INDIVIDUAL VIDEO LINKS\n" + links if links else "Previous dated lesson links: " + base + "/",
                 "MATERIALS\nAll 17 Blood Bank Guy teaching-library videos, all seven Morgan pathCast microbiology lectures, all 118 Sketchy Micro lessons and six selected chemistry/monitoring Path/Pharm lessons. The remaining 75 previously selected Path/Pharm lessons are optional, not extra nightly requirements. Full library: " + base + "/#video-library",
                 "FLEXIBLE PLAN\nStop at the time limit. Record unfinished lessons privately and move them to upcoming dates; do not automatically double the next night. Reduce lower-priority Path/Pharm before displacing question review or rest.",
                 "Next-day Anki: selected cards matching these lessons, after due CP reviews; avoid duplicating whole decks.",
                 "The 22:30 end and 05:00 start leave only 6.5 hours between blocks before wind-down. Finish early when possible; do not extend to catch up.",
                 "Study context: " + base + "/context.html"]
        if any("[Old Version]" in v["title"] for v in videos):
            notes.insert(4, "VERSION NOTE\nThe Hepatitis B life-cycle lesson is labeled Old Version by Sketchy. It is included for the requested full rewatch; use the current lesson and authoritative current references if details conflict.")
        if "Blood Bank Guy" in providers:
            notes.insert(4, "BLOOD BANK GUY\nThe teaching archive dates mostly to 2011-2014; Last Minute Essentials is from 2024. Check current guidance for changed policies, donor testing and terminology. Source pages include available handouts and corrections; for Antibody ID 2, work the handout panels before the explanation.\n" + "\n".join(dict.fromkeys(v["source_url"] for v in videos if v["course"] == "Blood Bank Guy")))
        if "Morgan" in providers:
            notes.insert(4, "MORGAN COMPANION MATERIAL\nThese are 2020-2021 recordings, not 2026 videos. Use the 2026 slides for updated terminology and testing details; slide review comes from the remaining recall time, not an additional full reading assignment.\n" + "\n".join(dict.fromkeys(v["source_url"] for v in videos if v["course"] == "Morgan")))
        result.append(dict(day=day, start=start, end=end, left=left,
                           title=f"CP Boards | {countdown} | {topic}", goal=goal,
                           materials=" + ".join(providers), description="\n\n".join(notes), status="CONFIRMED",
                           mode=kind, url=base + "/#" + anchor, context_url=base + "/context.html",
                           uid=f"{anchor}@{settings['namespace']}", anchor=anchor,
                           videos=videos, video_minutes=minutes))
    if seen_lessons != set(catalog) - optional:
        raise ValueError("Every selected lesson must have one dated assignment")
    return sorted(result, key=lambda s: s["start"])


def build_calendar(plan: dict, sessions: list[dict]) -> bytes:
    settings = plan["settings"]
    calendar = Calendar()
    calendar.add("prodid", "-//CP Boards Study Calendar//EN")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("method", "PUBLISH")
    calendar.add("x-wr-calname", settings["title"])
    calendar.add("x-wr-caldesc", plan["strategy"]["objective"])
    calendar.add("refresh-interval", timedelta(hours=1), parameters={"VALUE": "DURATION"})
    calendar.add("x-published-ttl", "PT1H")
    for session in sessions:
        event = Event()
        event.add("uid", session["uid"])
        event.add("dtstamp", settings["updated_at"])
        event.add("last-modified", settings["updated_at"])
        event.add("sequence", settings["sequence"])
        event.add("dtstart", session["start"])
        event.add("dtend", session["end"])
        event.add("summary", session["title"])
        event.add("description", session["description"])
        event.add("status", session["status"])
        event.add("transp", "OPAQUE")
        event.add("url", session["url"])
        event.add("attach", session["context_url"], parameters={"FMTTYPE": "text/html"})
        event.add("categories", ["CP Boards", "Study"])
        calendar.add_component(event)
    return calendar.to_ical()


def build_rss(plan: dict, sessions: list[dict]) -> bytes:
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    for name, value in {"title": "CP Boards Study Plan", "link": plan["settings"]["site_url"],
                        "description": plan["strategy"]["objective"],
                        "lastBuildDate": format_datetime(plan["settings"]["updated_at"])}.items():
        ET.SubElement(channel, name).text = value
    for session in sessions:
        item = ET.SubElement(channel, "item")
        title = session["title"] if session["status"] != "CANCELLED" else "Cancelled: " + session["title"]
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = session["url"]
        ET.SubElement(item, "guid", isPermaLink="false").text = session["uid"]
        ET.SubElement(item, "pubDate").text = format_datetime(plan["settings"]["updated_at"])
        ET.SubElement(item, "description").text = (
            f"{session['day'].isoformat()} {session['start']:%H:%M}-{session['end']:%H:%M} local.\n\n" + session["description"]
        )
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def video_library(catalog: dict, allocation: dict, sessions: list[dict]) -> str:
    escape = html.escape
    optional = set(allocation.get("optional_lessons", []))
    assignments = {v["path"]: session for session in sessions for v in session.get("videos", [])}
    groups = []
    for course in ("Blood Bank Guy", "Morgan", "Micro", "Path", "Pharm"):
        videos = {}
        for key, video in catalog.items():
            if video["course"] == course:
                videos.setdefault(video.get("id", key), []).append(video)
        links = []
        for parts in videos.values():
            video = parts[0]
            assigned = [assignments[p["path"]] for p in parts if p["path"] in assignments]
            title = video["title"].split(" | Part ")[0]
            url = video["url"].split("&t=")[0]
            timing = timestamp(video["seconds"]) if "seconds" in video else f"~{video['minutes']} min"
            dates = ", ".join(f'<a href="#{s["anchor"]}">{s["day"]:%b %d}</a>' for s in assigned)
            label = "Optional, not assigned" if video["path"] in optional else dates
            source = (f' | <a href="{escape(video["source_url"], quote=True)}">2026 slides</a>' if course == "Morgan"
                      else f' | <a href="{escape(video["source_url"], quote=True)}">Source / handouts / corrections</a>' if course == "Blood Bank Guy" else "")
            links.append(f'<li><a href="{escape(url, quote=True)}">{escape(title)}</a> <small>{timing}</small><br>{label}{source}</li>')
        groups.append(f'<details class="video-group"><summary><span>{escape(course)} ({len(videos)} videos)</span></summary><ul>{"".join(links)}</ul></details>')
    return "".join(groups)


def write_pages(plan: dict, sessions: list[dict], public: Path, root: Path = ROOT) -> None:
    settings = plan["settings"]
    base = settings["site_url"].rstrip("/")
    escape = html.escape
    entries = []
    for session in sessions:
        cancelled = " (cancelled)" if session["status"] == "CANCELLED" else ""
        lesson_links = ""
        if session.get("videos"):
            lesson_links = '<ol class="lesson-links">' + "".join(
                f'<li><a href="{escape(v["url"], quote=True)}">[{escape(v["course"])}] {escape(v["title"])}</a> <small>~{v["minutes"]} min</small></li>'
                for v in session["videos"]) + "</ol>"
        if session.get("question_links") and session["mode"] != "light":
            lesson_links += '<nav class="question-links" aria-label="Question bank setup">' + "".join(
                f'<a href="{escape(url, quote=True)}">{escape(label)}</a>' for label, url in session["question_links"]) + '</nav>'
        entries.append(f'''<details id="{session['anchor']}">
<summary><time datetime="{session['day'].isoformat()}">{session['day']:%a, %b %d}</time><span>{escape(session['title'])}{cancelled}</span><small>{session['start']:%H:%M}-{session['end']:%H:%M}</small></summary>
{lesson_links}<p class="notes">{escape(session['description'])}</p></details>''')
    template = (root / "templates/index.html").read_text()
    default_start = time.fromisoformat(settings["start"])
    default_end = datetime.combine(settings["start_date"], default_start) + timedelta(minutes=settings["duration_minutes"])
    schedule = f"{default_start:%H:%M}-{default_end:%H:%M} local daily; {settings['start_date']:%B %d}-{sessions[-1]['day']:%B %d}"
    evenings = [s for s in sessions if "videos" in s]
    if evenings:
        schedule += f". Videos {evenings[0]['start']:%H:%M}-{evenings[0]['end']:%H:%M}, {evenings[0]['day']:%B %d}-{evenings[-1]['day']:%B %d}; final two nights light"
    tokens = {"@@BASE@@": escape(base), "@@EXAM@@": settings["exam_date"].isoformat(),
              "@@EXAM_LABEL@@": settings["exam_date"].strftime("%B %d, %Y"),
              "@@SCHEDULE@@": escape(schedule), "@@WEBCAL@@": escape(base.replace("https://", "webcal://", 1) + "/cp-study.ics"),
              "@@EVENTS@@": "\n".join(entries), "@@COUNT@@": str(len(sessions)),
              "@@REPO@@": escape(settings["repository_url"]),
              "@@OBJECTIVE@@": escape(plan["strategy"]["objective"]),
              "@@QUESTION_SUMMARY@@": ''.join(f'<p>{escape(plan["strategy"][key])}</p>' for key in ("question_plan", "capacity")),
              "@@VIDEO_SUMMARY@@": escape(plan["strategy"]["videos"]),
              "@@VIDEO_LIBRARY@@": video_library(read_all_videos(root), json.loads((root / "video_plan.json").read_text()), sessions)}
    for token, value in tokens.items():
        template = template.replace(token, value)
    (public / "index.html").write_text(template, encoding="utf-8")
    sections = "".join(f"<p>{escape(value)}</p>" for value in plan["strategy"].values() if isinstance(value, str))
    (public / "context.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>CP Study Context</title><style>body{font:17px/1.6 system-ui;margin:32px auto;max-width:760px;padding:0 20px;color:#222}a{color:#246da7;overflow-wrap:anywhere}</style>'
        '<main><h1>CP Study Context</h1>' + sections +
        f'<p><a href="{escape(settings["repository_url"] + "/blob/main/context.md")}">Full strategy and sources</a></p>'
        f'<p><a href="{escape(base)}">Study calendar</a></p></main></html>', encoding="utf-8")
    (public / ".nojekyll").touch()


def generate(root: Path = ROOT) -> list[dict]:
    plan = read_plan(root / "plan.toml")
    questions = read_question_plan(root / "question_plan.csv", plan)
    sessions = build_sessions(plan, questions)
    allocation = json.loads((root / "video_plan.json").read_text())
    sessions += build_video_sessions(plan, allocation, read_all_videos(root))
    sessions.sort(key=lambda s: s["start"])
    public = root / "public"
    public.mkdir(exist_ok=True)
    (public / "question-plan.csv").write_bytes((root / "question_plan.csv").read_bytes())
    (public / "cp-study.ics").write_bytes(build_calendar(plan, sessions))
    (public / "rss.xml").write_bytes(build_rss(plan, sessions))
    write_pages(plan, sessions, public, root)
    print(f"Generated {len(sessions)} dated blocks; {sessions[0]['left']} to {sessions[-1]['left']} days left")
    return sessions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    generate(parser.parse_args().root)
