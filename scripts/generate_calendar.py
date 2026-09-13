#!/usr/bin/env python3
"""Generate a dated study calendar and RSS feed from the editable TOML plan."""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
from email.utils import format_datetime
import html
import json
from pathlib import Path
import tomllib
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from icalendar import Calendar, Event


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


def routine(mode: str, start: datetime, duration: int, target: int) -> str:
    if mode == "light":
        return "Light session: 20-40 minutes of familiar recall and logistics. The remaining reserved time is optional. No new broad material."
    if duration != 120:
        return f"Adapt this {duration}-minute session: questions, priority explanations, selected recall, then a brief progress log. Reduce the {target}-question target if needed."
    steps = (
        [(0, 66, "55-question timed mixed block"), (66, 110, "Review priority misses and uncertain answers"), (110, 120, "List unresolved explanations and log actual work")]
        if mode == "timed"
        else [(0, 60, "Targeted reading for today's topic and prior misses; do not read the entire guide first"), (60, 115, "PathDojo: fresh questions plus due incorrect-question redos, with explanations"), (115, 120, "Log new questions, redos, repeated misses and remaining review")]
    )
    return "\n".join(
        f"{(start + timedelta(minutes=a)):%H:%M}-{(start + timedelta(minutes=b)):%H:%M}: {label}"
        for a, b, label in steps
    ) + "\nAnki is distributed through the day. The question hour is time-boxed, not a promise that the full-bank completion target fits. Log overflow and revise upcoming work."


def build_sessions(plan: dict) -> list[dict]:
    validate_plan(plan)
    settings, strategy = plan["settings"], plan["strategy"]
    sessions = []
    day = settings["start_date"]
    while day < settings["exam_date"]:
        override = plan.get("overrides", {}).get(day.isoformat(), {})
        topic_id = override.get("topic", plan["weekly"][DAYS[day.weekday()]])
        if topic_id not in plan["topics"]:
            raise ValueError(f"Unknown topic: {topic_id}")
        topic = plan["topics"][topic_id]
        mode = override.get("mode", "practice")
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
        title = f"CP Boards | {countdown} | {topic['title']}"
        target = int(override.get("question_target", strategy["default_question_target"]))
        if target < 0:
            raise ValueError("Question target must be nonnegative")
        goal = override.get("goal", topic["goal"])
        materials = override.get("materials", topic["materials"])
        context_url = settings["site_url"].rstrip("/") + "/context.html"
        url = settings["site_url"].rstrip("/") + "/#study-" + day.isoformat()
        resource_text = "\n".join(f"{key}: {plan['resources'][key]}" for key in topic["links"])
        description = "\n\n".join(filter(None, [
            f"{countdown.capitalize()} until the CP exam on {settings['exam_date']:%B %d, %Y}. Countdown is from this study date.",
            strategy["objective"], "TODAY\n" + goal,
            "SESSION\n" + routine(mode, start, duration, target),
            strategy["review_rule"], strategy["anki_rule"],
            "MATERIALS\n" + materials, override.get("note", ""),
            "FLEXIBLE PLAN\n" + strategy["flexibility"] + " " + strategy["capacity"],
            strategy["gym"], "RESOURCE LINKS\n" + resource_text,
            "Study context: " + context_url,
            "Editable plan: " + settings["repository_url"] + "/blob/main/plan.toml",
        ]))
        sessions.append(dict(day=day, start=start, end=end, left=left, title=title,
                             goal=goal, materials=materials, description=description,
                             status=status, mode=mode, url=url, context_url=context_url,
                             anchor=f"study-{day.isoformat()}",
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


def build_video_sessions(plan: dict, allocation: dict, catalog: dict) -> list[dict]:
    settings = plan["settings"]
    start_time = time.fromisoformat(allocation["start"])
    duration = int(allocation["duration_minutes"])
    limit = int(allocation["max_video_minutes"])
    if start_time.tzinfo or not 0 < limit <= duration - 10 or duration > 180:
        raise ValueError("Videos must leave at least ten minutes for recall")
    result, seen_dates, seen_lessons = [], set(), set()
    for item in allocation["sessions"]:
        day = date.fromisoformat(item["date"])
        if day in seen_dates or not settings["start_date"] <= day < settings["exam_date"]:
            raise ValueError("Duplicate or out-of-range video date")
        seen_dates.add(day)
        kind = item["kind"]
        if kind not in {"watch", "review", "light"} or (kind == "watch") != bool(item["lessons"]):
            raise ValueError("Invalid video session kind")
        videos = []
        for key in item["lessons"]:
            if key in seen_lessons or key not in catalog:
                raise ValueError("Duplicate or unknown assigned lesson")
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
        topic = "Sketchy | " + (f"{len(videos)} videos" if videos else "Light recall" if kind == "light" else "Catch-up + recall")
        anchor = f"video-{day.isoformat()}"
        base = settings["site_url"].rstrip("/")
        goal = ("Rewatch all assigned lessons, including those previously marked completed. Explain a diagnostic distinction after each."
                if videos else "No new lessons. Optional 15-20 minutes of familiar recall, then stop early and protect rest."
                if kind == "light" else "Use this buffer for unfinished assigned lessons or recurring weak concepts. Do not add a new course.")
        links = "\n\n".join(f"{i}. [{v['course']}] {v['title']} (~{v['minutes']} min)\n{v['url']}"
                              for i, v in enumerate(videos, 1))
        notes = [f"{countdown.capitalize()} until the CP exam on {settings['exam_date']:%B %d, %Y}.",
                 "TODAY\n" + goal,
                 f"SESSION\n{start:%H:%M}-{end:%H:%M} reserved. Approximately {minutes} minutes of video at normal speed; {duration - minutes} minutes remain for pauses, recall and a brief log. Displayed durations are rounded, not second-exact." if videos else f"SESSION\n{start:%H:%M}-{end:%H:%M} reserved; unused time is optional.",
                 "INDIVIDUAL VIDEO LINKS\n" + links if links else "Previous dated lesson links: " + base + "/",
                 "MATERIALS\nAll Sketchy Micro plus selected CP-focused Path/Pharm. Unit tests are not counted as videos. These lessons support, but do not replace, laboratory methods, transfusion, molecular and management practice.",
                 "FLEXIBLE PLAN\nStop at the time limit. Record unfinished lessons privately and move them to upcoming dates; do not automatically double the next night. Reduce lower-priority Path/Pharm before displacing question review or rest.",
                 "Next-day Anki: selected cards matching these lessons, after due CP reviews; avoid duplicating whole decks.",
                 "The 22:30 end and 05:00 start leave only 6.5 hours between blocks before wind-down. Finish early when possible; do not extend to catch up.",
                 "Study context: " + base + "/context.html"]
        if any("[Old Version]" in v["title"] for v in videos):
            notes.insert(4, "VERSION NOTE\nThe Hepatitis B life-cycle lesson is labeled Old Version by Sketchy. It is included for the requested full rewatch; use the current lesson and authoritative current references if details conflict.")
        result.append(dict(day=day, start=start, end=end, left=left,
                           title=f"CP Boards | {countdown} | {topic}", goal=goal,
                           materials="Sketchy", description="\n\n".join(notes), status="CONFIRMED",
                           mode=kind, url=base + "/#" + anchor, context_url=base + "/context.html",
                           uid=f"{anchor}@{settings['namespace']}", anchor=anchor,
                           videos=videos, video_minutes=minutes))
    if seen_lessons != set(catalog):
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
                f'<li><a href="{escape(v["url"], quote=True)}">{escape(v["title"])}</a> <small>{v["minutes"]} min</small></li>'
                for v in session["videos"]) + "</ol>"
        entries.append(f'''<details id="{session['anchor']}">
<summary><time datetime="{session['day'].isoformat()}">{session['day']:%a, %b %d}</time><span>{escape(session['title'])}{cancelled}</span><small>{session['start']:%H:%M}-{session['end']:%H:%M}</small></summary>
{lesson_links}<p class="notes">{escape(session['description'])}</p></details>''')
    template = (root / "templates/index.html").read_text()
    default_start = time.fromisoformat(settings["start"])
    default_end = datetime.combine(settings["start_date"], default_start) + timedelta(minutes=settings["duration_minutes"])
    schedule = f"{default_start:%H:%M}-{default_end:%H:%M} local daily; {settings['start_date']:%B %d}-{sessions[-1]['day']:%B %d}"
    evenings = [s for s in sessions if "videos" in s]
    if evenings:
        schedule += f". Sketchy {evenings[0]['start']:%H:%M}-{evenings[0]['end']:%H:%M}, {evenings[0]['day']:%B %d}-{evenings[-1]['day']:%B %d}; final two nights light"
    tokens = {"@@BASE@@": escape(base), "@@EXAM@@": settings["exam_date"].isoformat(),
              "@@EXAM_LABEL@@": settings["exam_date"].strftime("%B %d, %Y"),
              "@@SCHEDULE@@": escape(schedule), "@@WEBCAL@@": escape(base.replace("https://", "webcal://", 1) + "/cp-study.ics"),
              "@@EVENTS@@": "\n".join(entries), "@@COUNT@@": str(len(sessions)),
              "@@REPO@@": escape(settings["repository_url"]),
              "@@OBJECTIVE@@": escape(plan["strategy"]["objective"])}
    for token, value in tokens.items():
        template = template.replace(token, value)
    (public / "index.html").write_text(template, encoding="utf-8")
    sections = "".join(f"<p>{escape(value)}</p>" for value in plan["strategy"].values() if isinstance(value, str))
    (public / "context.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>CP Study Context</title><style>body{font:17px/1.6 system-ui;margin:32px auto;max-width:760px;padding:0 20px;color:#222}a{color:#12624f}</style>'
        '<main><h1>CP Study Context</h1>' + sections +
        f'<p><a href="{escape(settings["repository_url"] + "/blob/main/context.md")}">Full strategy and sources</a></p>'
        f'<p><a href="{escape(base)}">Study calendar</a></p></main></html>', encoding="utf-8")
    (public / ".nojekyll").touch()


def generate(root: Path = ROOT) -> list[dict]:
    plan = read_plan(root / "plan.toml")
    sessions = build_sessions(plan)
    allocation = json.loads((root / "video_plan.json").read_text())
    sessions += build_video_sessions(plan, allocation, read_video_catalog(root / "video_catalog.tsv"))
    sessions.sort(key=lambda s: s["start"])
    public = root / "public"
    public.mkdir(exist_ok=True)
    (public / "cp-study.ics").write_bytes(build_calendar(plan, sessions))
    (public / "rss.xml").write_bytes(build_rss(plan, sessions))
    write_pages(plan, sessions, public, root)
    print(f"Generated {len(sessions)} dated blocks; {sessions[0]['left']} to {sessions[-1]['left']} days left")
    return sessions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    generate(parser.parse_args().root)
