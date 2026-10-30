from __future__ import annotations

import os
import json
import sqlite3
from contextlib import contextmanager
from calendar import Calendar, monthrange
from datetime import date, datetime, timedelta

from urllib.parse import quote, urlparse

from flask import Flask, abort, jsonify, render_template, request

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "instance", "todo.db")
CATEGORY_LABELS = {
    "work": "Công việc",
    "personal": "Cá nhân",
    "health": "Sức khỏe",
    "study": "Học tập",
    "group_meeting": "Họp nhóm",
    "other": "Khác",
}
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


@contextmanager
def connect_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def init_db():
    with connect_db() as db:
        db.execute(
                """CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    category TEXT NOT NULL DEFAULT 'personal',
                    repeat_rule TEXT NOT NULL DEFAULT 'none',
                    repeat_until TEXT,
                    notes TEXT DEFAULT '',
                    zoom_link TEXT DEFAULT '',
                    zoom_id TEXT DEFAULT '',
                    zoom_password TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(events)").fetchall()}
        if "category" not in columns:
            db.execute("ALTER TABLE events ADD COLUMN category TEXT NOT NULL DEFAULT 'personal'")
        if "zoom_link" not in columns:
            db.execute("ALTER TABLE events ADD COLUMN zoom_link TEXT DEFAULT ''")
        if "zoom_id" not in columns:
            db.execute("ALTER TABLE events ADD COLUMN zoom_id TEXT DEFAULT ''")
        if "zoom_password" not in columns:
            db.execute("ALTER TABLE events ADD COLUMN zoom_password TEXT DEFAULT ''")
        if "missions" not in columns:
            db.execute("ALTER TABLE events ADD COLUMN missions TEXT NOT NULL DEFAULT '[]'")
        if "repeat_days" not in columns:
            db.execute("ALTER TABLE events ADD COLUMN repeat_days TEXT NOT NULL DEFAULT '[]'")
        if "repeat_interval" not in columns:
            db.execute("ALTER TABLE events ADD COLUMN repeat_interval INTEGER NOT NULL DEFAULT 1")
        db.execute(
                """CREATE TABLE IF NOT EXISTS completions (
                    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                    occurrence_date TEXT NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (event_id, occurrence_date)
                )"""
            )
        db.execute(
            """CREATE TABLE IF NOT EXISTS mission_completions (
                event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                occurrence_date TEXT NOT NULL,
                mission_index INTEGER NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (event_id, occurrence_date, mission_index)
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS occurrence_statuses (
                event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                occurrence_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'planned',
                note TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (event_id, occurrence_date)
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS reflections (
                period_type TEXT NOT NULL,
                period_start TEXT NOT NULL,
                proud TEXT NOT NULL DEFAULT '',
                improve TEXT NOT NULL DEFAULT '',
                lesson TEXT NOT NULL DEFAULT '',
                memory TEXT NOT NULL DEFAULT '',
                pattern TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (period_type, period_start)
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS goals (
                period_type TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                goal_text TEXT NOT NULL DEFAULT '',
                reason TEXT NOT NULL DEFAULT '',
                first_step TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (period_type, period_start)
            )"""
        )


def period_bounds(anchor: date, period: str):
    if period == "day":
        return anchor, anchor
    if period == "month":
        return anchor.replace(day=1), anchor.replace(day=monthrange(anchor.year, anchor.month)[1])
    if period == "quarter":
        month = ((anchor.month - 1) // 3) * 3 + 1
        start = date(anchor.year, month, 1)
        end_month = month + 2
        return start, date(anchor.year, end_month, monthrange(anchor.year, end_month)[1])
    if period == "year":
        return date(anchor.year, 1, 1), date(anchor.year, 12, 31)
    start = anchor - timedelta(days=anchor.weekday())
    return start, start + timedelta(days=6)


def next_goal_period(today: date, period: str):
    if period == "week":
        start = today - timedelta(days=today.weekday()) + timedelta(days=7)
    elif period == "month":
        start = date(today.year + (today.month == 12), today.month % 12 + 1, 1)
    else:
        next_month = ((today.month - 1) // 3 + 1) * 3 + 1
        year = today.year + (1 if next_month > 12 else 0)
        start = date(year, ((next_month - 1) % 12) + 1, 1)
    _, end = period_bounds(start, period)
    return start, end


def occurs_on(event, day: date) -> bool:
    first = date.fromisoformat(str(event["event_date"]))
    until = date.fromisoformat(str(event["repeat_until"])) if event["repeat_until"] else None
    if day < first or (until and day > until):
        return False
    rule = event["repeat_rule"]
    if rule == "none":
        return day == first
    if rule == "daily":
        return True
    if rule == "weekly":
        try:
            repeat_days = json.loads(event["repeat_days"] or "[]")
        except (TypeError, json.JSONDecodeError):
            repeat_days = []
        weekdays = {int(value) for value in repeat_days if str(value).isdigit()} if repeat_days else {first.weekday()}
        interval = max(1, int(event["repeat_interval"] or 1))
        first_week = first - timedelta(days=first.weekday())
        current_week = day - timedelta(days=day.weekday())
        week_number = (current_week - first_week).days // 7
        return week_number % interval == 0 and day.weekday() in weekdays
    if rule == "monthly":
        return day.day == first.day and (day.year, day.month) >= (first.year, first.month)
    return day == first


def get_occurrences(start: date, end: date, category: str | None = None):
    with connect_db() as db:
        query = "SELECT * FROM events WHERE event_date <= ?"
        params = [end.isoformat()]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY start_time"
        events = db.execute(query, params).fetchall()
        done_rows = db.execute(
            "SELECT event_id, occurrence_date FROM completions WHERE completed = 1 AND occurrence_date BETWEEN ? AND ?",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        mission_rows = db.execute(
            """SELECT event_id, occurrence_date, mission_index FROM mission_completions
               WHERE completed = 1 AND occurrence_date BETWEEN ? AND ?""",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        status_rows = db.execute(
            """SELECT event_id, occurrence_date, status, note FROM occurrence_statuses
               WHERE occurrence_date BETWEEN ? AND ?""",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    done = {(row["event_id"], str(row["occurrence_date"])) for row in done_rows}
    mission_done = {(row["event_id"], str(row["occurrence_date"]), row["mission_index"]) for row in mission_rows}
    statuses = {(row["event_id"], str(row["occurrence_date"])): (row["status"], row["note"]) for row in status_rows}
    by_day = {}
    day = start
    while day <= end:
        items = []
        for event in events:
            if occurs_on(event, day):
                try:
                    mission_titles = json.loads(event["missions"] or "[]")
                except (TypeError, json.JSONDecodeError):
                    mission_titles = []
                items.append({
                    **dict(event),
                    "missions": [
                        {"index": index, "title": title, "completed": (event["id"], day.isoformat(), index) in mission_done}
                        for index, title in enumerate(mission_titles)
                    ],
                    "completed": (event["id"], day.isoformat()) in done,
                    "occurrence_date": day.isoformat(),
                    "occurrence_status": statuses.get((event["id"], day.isoformat()), ("planned", ""))[0],
                    "status_note": statuses.get((event["id"], day.isoformat()), ("planned", ""))[1],
                })
        by_day[day.isoformat()] = items
        day += timedelta(days=1)
    return by_day


def layout_calendar(occurrences: dict, start_hour: int = 7, end_hour: int = 24):
    """Prepare positioned event cards for the detailed day/week calendar."""
    start_minute = start_hour * 60
    end_minute = end_hour * 60
    calendar = {}
    for day_key, events in occurrences.items():
        positioned = []
        for event in sorted(events, key=lambda item: item["start_time"]):
            start_time = datetime.strptime(str(event["start_time"])[:5], "%H:%M")
            end_time = datetime.strptime(str(event["end_time"])[:5], "%H:%M")
            event_start = max(start_time.hour * 60 + start_time.minute, start_minute)
            raw_end = end_time.hour * 60 + end_time.minute
            event_end = raw_end + (24 * 60 if raw_end <= start_time.hour * 60 + start_time.minute else 0)
            event_end = min(event_end, end_minute)
            if event_end <= event_start:
                continue
            positioned.append({
                **dict(event),
                "calendar_start": event_start,
                "calendar_end": event_end,
            })

        # Split only connected groups of events whose time ranges overlap.
        clusters = []
        cluster = []
        cluster_end = None
        for event in positioned:
            if cluster and event["calendar_start"] >= cluster_end:
                clusters.append(cluster)
                cluster = []
                cluster_end = None
            cluster.append(event)
            cluster_end = max(cluster_end or event["calendar_end"], event["calendar_end"])
        if cluster:
            clusters.append(cluster)

        for cluster in clusters:
            lanes = []
            for event in cluster:
                lane = next((index for index, lane_end in enumerate(lanes) if lane_end <= event["calendar_start"]), len(lanes))
                if lane == len(lanes):
                    lanes.append(event["calendar_end"])
                else:
                    lanes[lane] = event["calendar_end"]
                event["calendar_lane"] = lane

            lane_count = max(1, len(lanes))
            lane_events = [[event for event in cluster if event["calendar_lane"] == lane] for lane in range(lane_count)]
            for event in cluster:
                lane = event["calendar_lane"]
                span = 1
                for next_lane in range(lane + 1, lane_count):
                    overlaps = any(
                        event["calendar_start"] < other["calendar_end"]
                        and other["calendar_start"] < event["calendar_end"]
                        for other in lane_events[next_lane]
                    )
                    if overlaps:
                        break
                    span += 1
                event["calendar_top"] = event["calendar_start"] - start_minute
                event["calendar_height"] = max(38, event["calendar_end"] - event["calendar_start"])
                event["calendar_left"] = lane * 100 / lane_count
                event["calendar_width"] = span * 100 / lane_count
        calendar[day_key] = positioned
    return calendar


@app.get("/")
def dashboard():
    period = request.args.get("period", "week")
    if period not in {"day", "week", "month", "quarter", "year"}:
        period = "week"
    detail_view = request.args.get("view", "timeline")
    if detail_view not in {"timeline", "list", "category", "board"}:
        detail_view = "timeline"
    try:
        anchor = date.fromisoformat(request.args.get("date", date.today().isoformat()))
    except ValueError:
        anchor = date.today()
    category_filter = request.args.get("category", "all")
    if category_filter not in {"all", *CATEGORY_LABELS}:
        category_filter = "all"
    selected_category = None if category_filter == "all" else category_filter
    start, end = period_bounds(anchor, period)
    occurrences = get_occurrences(start, end, selected_category)
    calendar_occurrences = layout_calendar(occurrences)
    month_start = anchor.replace(day=1)
    month_end = anchor.replace(day=monthrange(anchor.year, anchor.month)[1])
    mini_occurrences = get_occurrences(month_start, month_end, selected_category)
    mini_event_dates = {day for day, items in mini_occurrences.items() if items}
    mini_calendar = [
        [
            {
                "date": day.isoformat(),
                "day": day.day,
                "in_month": day.month == anchor.month,
                "today": day == date.today(),
                "selected": day == anchor,
                "has_events": day.isoformat() in mini_event_dates,
            }
            for day in week
        ]
        for week in Calendar(firstweekday=0).monthdatescalendar(anchor.year, anchor.month)
    ]
    previous_month = month_start - timedelta(days=1)
    next_month = month_end + timedelta(days=1)
    total = sum(sum(item["occurrence_status"] not in {"cancelled", "rescheduled"} for item in items) for items in occurrences.values())
    done = sum(sum(item["completed"] and item["occurrence_status"] == "planned" for item in items) for items in occurrences.values())
    today_key = date.today().isoformat()
    today_items = get_occurrences(date.today(), date.today(), selected_category)[today_key]
    today_total = sum(item["occurrence_status"] not in {"cancelled", "rescheduled"} for item in today_items)
    today_done = sum(item["completed"] and item["occurrence_status"] == "planned" for item in today_items)
    now = datetime.now()
    now_minute = now.hour * 60 + now.minute
    now_calendar_top = now_minute - 7 * 60 if 7 * 60 <= now_minute < 24 * 60 else None
    prev_anchor = anchor - (end - start + timedelta(days=1))
    next_anchor = anchor + (end - start + timedelta(days=1))
    detail_occurrences = []
    for day_key, day_items in occurrences.items():
        for item in day_items:
            detail_occurrences.append({**item, "day_key": day_key})
    category_groups = {}
    for item in detail_occurrences:
        category_groups.setdefault(item["category"], []).append(item)
    board_groups = {"planned": [], "completed": [], "rescheduled": [], "cancelled": []}
    for item in detail_occurrences:
        lane = item["occurrence_status"] if item["occurrence_status"] != "planned" else ("completed" if item["completed"] else "planned")
        board_groups[lane].append(item)
    review_week_start, review_week_end = period_bounds(anchor, "week")
    review_month_start = anchor.replace(day=1)
    review_periods = {
        "week": review_week_start,
        "month": review_month_start,
    }
    goal_periods = {scope: next_goal_period(date.today(), scope) for scope in ("week", "month", "quarter")}
    with connect_db() as db:
        reflection_rows = db.execute(
            "SELECT * FROM reflections WHERE (period_type='week' AND period_start=?) OR (period_type='month' AND period_start=?)",
            (review_week_start.isoformat(), review_month_start.isoformat()),
        ).fetchall()
        goal_rows = db.execute(
            "SELECT * FROM goals WHERE period_type IN ('week', 'month', 'quarter')"
        ).fetchall()
    reflections = {row["period_type"]: dict(row) for row in reflection_rows}
    goals = {
        row["period_type"]: dict(row)
        for row in goal_rows
        if row["period_start"] == goal_periods[row["period_type"]][0].isoformat()
    }
    return render_template(
        "dashboard.html",
        period=period,
        category_filter=category_filter,
        category_labels=CATEGORY_LABELS,
        detail_view=detail_view,
        anchor=anchor,
        start=start,
        end=end,
        occurrences=occurrences,
        calendar_occurrences=calendar_occurrences,
        detail_occurrences=detail_occurrences,
        category_groups=category_groups,
        board_groups=board_groups,
        mini_calendar=mini_calendar,
        mini_month=anchor.strftime("Tháng %m, %Y"),
        previous_month=previous_month,
        next_month=next_month,
        total=total,
        done=done,
        today_items=today_items,
        today_done=today_done,
        today_total=today_total,
        now_calendar_top=now_calendar_top,
        prev_anchor=prev_anchor,
        next_anchor=next_anchor,
        today=date.today(),
        review_periods=review_periods,
        review_week_end=review_week_end,
        review_month_end=period_bounds(anchor, "month")[1],
        reflections=reflections,
        goal_periods=goal_periods,
        goals=goals,
    )


def normalize_event_data(data):
    title = str(data.get("title", "")).strip()
    if not title:
        return None, "Vui lòng nhập tên sự kiện."
    try:
        event_date = date.fromisoformat(data.get("event_date", ""))
        start_time = datetime.strptime(data.get("start_time", ""), "%H:%M").time()
        end_time = datetime.strptime(data.get("end_time", ""), "%H:%M").time()
    except (ValueError, TypeError):
        return None, "Ngày hoặc thời gian không hợp lệ."
    if end_time == start_time:
        return None, "Giờ kết thúc cần khác giờ bắt đầu. Nếu sự kiện kéo dài đến cùng giờ ngày hôm sau, hãy chọn ngày kết thúc khác giờ bắt đầu."
    priority = data.get("priority", "medium")
    repeat_rule = data.get("repeat_rule", "none")
    try:
        repeat_interval = int(data.get("repeat_interval", 1) or 1)
    except (TypeError, ValueError):
        return None, "Khoảng lặp không hợp lệ."
    if not 1 <= repeat_interval <= 52:
        return None, "Khoảng lặp phải từ 1 đến 52 tuần."
    if repeat_rule != "weekly":
        repeat_interval = 1
    raw_repeat_days = data.get("repeat_days", [])
    if isinstance(raw_repeat_days, str):
        try:
            raw_repeat_days = json.loads(raw_repeat_days) if raw_repeat_days.startswith("[") else [raw_repeat_days]
        except json.JSONDecodeError:
            return None, "Các thứ lặp lại không hợp lệ."
    if not isinstance(raw_repeat_days, list):
        raw_repeat_days = [raw_repeat_days]
    try:
        repeat_days = sorted({int(value) for value in raw_repeat_days if str(value).strip() != ""})
    except (TypeError, ValueError):
        return None, "Các thứ lặp lại không hợp lệ."
    if any(value < 0 or value > 6 for value in repeat_days):
        return None, "Các thứ lặp lại không hợp lệ."
    if repeat_rule == "weekly" and not repeat_days:
        repeat_days = [event_date.weekday()]
    if repeat_rule != "weekly":
        repeat_days = []
    category = data.get("category", "personal")
    if priority not in {"low", "medium", "high"} or repeat_rule not in {"none", "daily", "weekly", "monthly"}:
        return None, "Tùy chọn không hợp lệ."
    if category not in CATEGORY_LABELS:
        return None, "Danh mục không hợp lệ."
    zoom_link = str(data.get("zoom_link", "") or "").strip()
    if zoom_link:
        parsed = urlparse(zoom_link)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None, "Link tham gia không hợp lệ. Vui lòng nhập URL hợp lệ bắt đầu bằng http:// hoặc https://."
    zoom_id = str(data.get("zoom_id", "") or "").strip()
    if zoom_id:
        normalized_zoom_id = "".join(ch for ch in zoom_id if ch.isdigit())
        if not normalized_zoom_id:
            return None, "ID cuộc họp Zoom chỉ được chứa số."
        zoom_id = normalized_zoom_id
    zoom_password = str(data.get("zoom_password", "") or "").strip()
    raw_missions = data.get("missions", [])
    if isinstance(raw_missions, str):
        try:
            raw_missions = json.loads(raw_missions) if raw_missions.startswith("[") else raw_missions.splitlines()
        except json.JSONDecodeError:
            return None, "Danh sách mission không hợp lệ."
    if not isinstance(raw_missions, list):
        return None, "Danh sách mission không hợp lệ."
    missions = list(dict.fromkeys(str(mission).strip() for mission in raw_missions if str(mission).strip()))
    if len(missions) > 30 or any(len(mission) > 160 for mission in missions):
        return None, "Tối đa 30 mission, mỗi mission không quá 160 ký tự."
    if category != "group_meeting":
        zoom_link = ""
        zoom_id = ""
        zoom_password = ""
    elif not zoom_link and zoom_id:
        join_url = f"https://zoom.us/j/{zoom_id}"
        if zoom_password:
            join_url = f"{join_url}?pwd={quote(zoom_password)}"
        zoom_link = join_url
    repeat_until = data.get("repeat_until") or None
    if repeat_until:
        try:
            repeat_until = date.fromisoformat(repeat_until).isoformat()
        except ValueError:
            return None, "Ngày kết thúc lặp không hợp lệ."
        if date.fromisoformat(repeat_until) < event_date:
            return None, "Ngày kết thúc lặp phải sau ngày bắt đầu."
    return {
        "title": title,
        "event_date": event_date.isoformat(),
        "start_time": start_time.strftime("%H:%M"),
        "end_time": end_time.strftime("%H:%M"),
        "priority": priority,
        "category": category,
        "repeat_rule": repeat_rule,
        "repeat_interval": repeat_interval,
        "repeat_days": repeat_days,
        "repeat_until": repeat_until,
        "notes": str(data.get("notes", "")).strip(),
        "zoom_link": zoom_link,
        "zoom_id": zoom_id,
        "zoom_password": zoom_password,
        "missions": missions,
    }, None


@app.post("/api/events")
def create_event():
    data = request.get_json(silent=True) or request.form
    values, error = normalize_event_data(data)
    if error:
        return jsonify(error=error), 400
    with connect_db() as db:
        cur = db.cursor()
        cur.execute(
                """INSERT INTO events(title, event_date, start_time, end_time, priority, category, repeat_rule, repeat_interval, repeat_days, repeat_until, notes, zoom_link, zoom_id, zoom_password, missions, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) RETURNING id""",
                tuple(json.dumps(values[key], ensure_ascii=False) if key in {"missions", "repeat_days"} else values[key] for key in ("title", "event_date", "start_time", "end_time", "priority", "category", "repeat_rule", "repeat_interval", "repeat_days", "repeat_until", "notes", "zoom_link", "zoom_id", "zoom_password", "missions")),
        )
        event_id = cur.fetchone()["id"]
    return jsonify(id=event_id), 201


@app.get("/api/events/<int:event_id>")
def get_event(event_id):
    with connect_db() as db:
        event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not event:
        abort(404)
    result = dict(event)
    try:
        result["missions"] = json.loads(result.get("missions") or "[]")
    except (TypeError, json.JSONDecodeError):
        result["missions"] = []
    try:
        result["repeat_days"] = json.loads(result.get("repeat_days") or "[]")
    except (TypeError, json.JSONDecodeError):
        result["repeat_days"] = []
    return jsonify(result)


@app.put("/api/events/<int:event_id>")
def update_event(event_id):
    data = request.get_json(silent=True) or request.form
    values, error = normalize_event_data(data)
    if error:
        return jsonify(error=error), 400
    with connect_db() as db:
        existing = db.execute("SELECT missions FROM events WHERE id=?", (event_id,)).fetchone()
        if not existing:
            abort(404)
        serialized_missions = json.dumps(values["missions"], ensure_ascii=False)
        cur = db.execute(
            """UPDATE events SET title=?, event_date=?, start_time=?, end_time=?, priority=?, category=?,
               repeat_rule=?, repeat_interval=?, repeat_days=?, repeat_until=?, notes=?, zoom_link=?, zoom_id=?, zoom_password=?, missions=? WHERE id=?""",
            (*tuple(serialized_missions if key == "missions" else json.dumps(values[key], ensure_ascii=False) if key == "repeat_days" else values[key] for key in ("title", "event_date", "start_time", "end_time", "priority", "category", "repeat_rule", "repeat_interval", "repeat_days", "repeat_until", "notes", "zoom_link", "zoom_id", "zoom_password", "missions")), event_id),
        )
        if not cur.rowcount:
            abort(404)
        if existing["missions"] != serialized_missions:
            db.execute("DELETE FROM mission_completions WHERE event_id=?", (event_id,))
    return jsonify(id=event_id, updated=True)


@app.post("/api/events/<int:event_id>/missions/toggle")
def toggle_mission(event_id):
    data = request.get_json(silent=True) or {}
    try:
        occurrence = date.fromisoformat(data.get("occurrence_date", ""))
        mission_index = int(data.get("mission_index", -1))
    except (ValueError, TypeError):
        return jsonify(error="Mission hoặc ngày không hợp lệ."), 400
    with connect_db() as db:
        event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not event or not occurs_on(event, occurrence):
            abort(404)
        try:
            missions = json.loads(event["missions"] or "[]")
        except (TypeError, json.JSONDecodeError):
            missions = []
        if mission_index < 0 or mission_index >= len(missions):
            abort(404)
        row = db.execute(
            "SELECT completed FROM mission_completions WHERE event_id=? AND occurrence_date=? AND mission_index=?",
            (event_id, occurrence.isoformat(), mission_index),
        ).fetchone()
        completed = not (row and row["completed"])
        db.execute(
            """INSERT INTO mission_completions(event_id, occurrence_date, mission_index, completed)
               VALUES (?, ?, ?, ?) ON CONFLICT(event_id, occurrence_date, mission_index)
               DO UPDATE SET completed=excluded.completed""",
            (event_id, occurrence.isoformat(), mission_index, completed),
        )
    return jsonify(completed=bool(completed))


@app.post("/api/events/<int:event_id>/occurrence-status")
def update_occurrence_status(event_id):
    data = request.get_json(silent=True) or {}
    try:
        occurrence = date.fromisoformat(data.get("occurrence_date", ""))
    except (ValueError, TypeError):
        return jsonify(error="Ngày không hợp lệ."), 400
    status = str(data.get("status", "planned"))
    note = str(data.get("note", "") or "").strip()
    if status not in {"planned", "cancelled", "rescheduled"}:
        return jsonify(error="Trạng thái sự kiện không hợp lệ."), 400
    if len(note) > 300:
        return jsonify(error="Ghi chú trạng thái tối đa 300 ký tự."), 400
    with connect_db() as db:
        event = db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if not event or not occurs_on(event, occurrence):
            abort(404)
        if status == "planned" and not note:
            db.execute("DELETE FROM occurrence_statuses WHERE event_id=? AND occurrence_date=?", (event_id, occurrence.isoformat()))
        else:
            db.execute(
                """INSERT INTO occurrence_statuses(event_id, occurrence_date, status, note)
                   VALUES (?, ?, ?, ?) ON CONFLICT(event_id, occurrence_date)
                   DO UPDATE SET status=excluded.status, note=excluded.note""",
                (event_id, occurrence.isoformat(), status, note),
            )
    return jsonify(status=status, note=note)


@app.post("/api/events/<int:event_id>/toggle")
def toggle_event(event_id):
    data = request.get_json(silent=True) or {}
    try:
        occurrence = date.fromisoformat(data.get("occurrence_date", ""))
    except ValueError:
        return jsonify(error="Ngày không hợp lệ."), 400
    with connect_db() as db:
        cur = db.cursor()
        cur.execute("SELECT * FROM events WHERE id=?", (event_id,))
        event = cur.fetchone()
        if not event or not occurs_on(event, occurrence):
            abort(404)
        cur.execute(
            "SELECT completed FROM completions WHERE event_id=? AND occurrence_date=?",
            (event_id, occurrence.isoformat()),
        )
        row = cur.fetchone()
        completed = not (row and row["completed"])
        cur.execute(
            """INSERT INTO completions(event_id, occurrence_date, completed)
               VALUES (?, ?, ?)
               ON CONFLICT (event_id, occurrence_date) DO UPDATE SET completed=excluded.completed""",
            (event_id, occurrence.isoformat(), completed),
        )
    return jsonify(completed=bool(completed))


@app.delete("/api/events/<int:event_id>")
def delete_event(event_id):
    with connect_db() as db:
        cur = db.cursor()
        cur.execute("DELETE FROM events WHERE id=?", (event_id,))
        if not cur.rowcount:
            abort(404)
    return jsonify(deleted=True)


@app.post("/api/reflections")
def save_reflection():
    data = request.get_json(silent=True) or {}
    period = str(data.get("period", ""))
    if period not in {"week", "month"}:
        return jsonify(error="Chọn tổng kết tuần hoặc tháng."), 400
    try:
        start = date.fromisoformat(str(data.get("period_start", "")))
    except ValueError:
        return jsonify(error="Ngày tổng kết không hợp lệ."), 400
    if period_bounds(start, period)[0] != start:
        return jsonify(error="Ngày bắt đầu kỳ tổng kết không hợp lệ."), 400
    fields = ("proud", "improve", "lesson", "memory", "pattern")
    values = {field: str(data.get(field, "") or "").strip() for field in fields}
    if any(len(value) > 4000 for value in values.values()):
        return jsonify(error="Mỗi câu trả lời tối đa 4.000 ký tự."), 400
    with connect_db() as db:
        db.execute(
            """INSERT INTO reflections(period_type, period_start, proud, improve, lesson, memory, pattern)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(period_type, period_start) DO UPDATE SET
               proud=excluded.proud, improve=excluded.improve, lesson=excluded.lesson,
               memory=excluded.memory, pattern=excluded.pattern""",
            (period, start.isoformat(), *(values[field] for field in fields)),
        )
    return jsonify(saved=True, period=period, period_start=start.isoformat())


@app.post("/api/goals")
def save_goal():
    data = request.get_json(silent=True) or {}
    period = str(data.get("period", ""))
    if period not in {"week", "month", "quarter"}:
        return jsonify(error="Chọn mục tiêu tuần, tháng hoặc quý."), 400
    try:
        start = date.fromisoformat(str(data.get("period_start", "")))
        end = date.fromisoformat(str(data.get("period_end", "")))
    except ValueError:
        return jsonify(error="Khoảng thời gian mục tiêu không hợp lệ."), 400
    if period_bounds(start, period) != (start, end):
        return jsonify(error="Khoảng thời gian mục tiêu không hợp lệ."), 400
    goal_text = str(data.get("goal_text", "") or "").strip()
    reason = str(data.get("reason", "") or "").strip()
    first_step = str(data.get("first_step", "") or "").strip()
    if not goal_text:
        return jsonify(error="Hãy viết một mục tiêu bạn muốn hướng tới."), 400
    if any(len(value) > limit for value, limit in ((goal_text, 500), (reason, 1000), (first_step, 500))):
        return jsonify(error="Mục tiêu hoặc câu trả lời vượt quá độ dài cho phép."), 400
    with connect_db() as db:
        db.execute(
            """INSERT INTO goals(period_type, period_start, period_end, goal_text, reason, first_step)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(period_type, period_start) DO UPDATE SET
               period_end=excluded.period_end, goal_text=excluded.goal_text,
               reason=excluded.reason, first_step=excluded.first_step""",
            (period, start.isoformat(), end.isoformat(), goal_text, reason, first_step),
        )
    return jsonify(saved=True, period=period, period_start=start.isoformat())


@app.get("/api/history")
def get_history():
    with connect_db() as db:
        reflections = db.execute(
            """SELECT * FROM reflections
               WHERE proud != '' OR improve != '' OR lesson != '' OR memory != '' OR pattern != ''
               ORDER BY period_start DESC LIMIT 100"""
        ).fetchall()
        goals = db.execute(
            """SELECT * FROM goals WHERE goal_text != ''
               ORDER BY period_start DESC LIMIT 100"""
        ).fetchall()
    return jsonify(reflections=[dict(row) for row in reflections], goals=[dict(row) for row in goals])


@app.get("/health")
def health():
    return jsonify(status="ok", app="To-Do Dashboard")


init_db()

if __name__ == "__main__":
    app.run(debug=True)
