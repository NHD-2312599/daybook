#!/usr/bin/env python3
"""
ĐL-T4 Dashboard – Flask App
Quản lý điểm danh NLSS / Mana / Chakki / Jondo + Suy ngẫm + Báo cáo tuần
"""

import json
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # hỗ trợ tiếng Việt

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "dl_t4_data.json")
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("STORAGE_POSTGRES_URL")
    or os.environ.get("STORAGE_DATABASE_URL")
    or os.environ.get("STORAGE_DATABASE_URL_UNPOOLED")
    or os.environ.get("STORAGE_POSTGRES_URL_NON_POOLING")
    or os.environ.get("POSTGRES_URL_NON_POOLING")
)

# ===== MEMBERS (cố định) =====
MEMBERS = [
    {"id": 1, "name": "Cil Thanh", "role": "JYJN"},
    {"id": 2, "name": "Nguyễn Thị Diệu Ngân", "role": "GYJN"},
    {"id": 3, "name": "Phạm Thị Thanh Thảo", "role": "JMN"},
    {"id": 4, "name": "Lê Nguyễn Quỳnh Như", "role": "JMN"},
    {"id": 5, "name": "Phạm Tường Vy", "role": "JMN"},
    {"id": 6, "name": "Phạm Minh Phước", "role": "HJN"},
    {"id": 7, "name": "Nguyễn Huỳnh Đức", "role": "HJN"},
    {"id": 8, "name": "Phạm Trịnh Khánh An", "role": "JMN"},
]


def load_data():
    if DATABASE_URL:
        import psycopg

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                _ensure_database(cur)
                cur.execute("SELECT payload FROM app_state WHERE id = 1")
                row = cur.fetchone()
                return row[0] if row else {}

    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_data(data):
    if DATABASE_URL:
        import psycopg

        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                _ensure_database(cur)
                cur.execute(
                    "UPDATE app_state SET payload = %s::jsonb, updated_at = NOW() WHERE id = 1",
                    (json.dumps(data, ensure_ascii=False),),
                )
        return

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _ensure_database(cursor):
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS app_state ("
        "id SMALLINT PRIMARY KEY CHECK (id = 1), "
        "payload JSONB NOT NULL, "
        "updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"
    )
    # Import local JSON once when bootstrapping a fresh database, if present.
    initial_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                initial_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            initial_data = {}
    cursor.execute(
        "INSERT INTO app_state (id, payload) VALUES (1, %s::jsonb) ON CONFLICT (id) DO NOTHING",
        (json.dumps(initial_data, ensure_ascii=False),),
    )


def update_data(mutator):
    """Apply a read-modify-write under a database row lock when using Postgres."""
    if not DATABASE_URL:
        data = load_data()
        mutator(data)
        save_data(data)
        return

    import psycopg

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            _ensure_database(cur)
            cur.execute("SELECT payload FROM app_state WHERE id = 1 FOR UPDATE")
            data = cur.fetchone()[0]
            mutator(data)
            cur.execute(
                "UPDATE app_state SET payload = %s::jsonb, updated_at = NOW() WHERE id = 1",
                (json.dumps(data, ensure_ascii=False),),
            )


# ===== ROUTES =====

@app.route("/")
def index():
    return render_template("index.html", members=MEMBERS)


@app.route("/api/members")
def api_members():
    return jsonify(MEMBERS)


@app.route("/api/data", methods=["GET"])
def api_get_data():
    """Lấy toàn bộ dữ liệu hoặc theo ngày"""
    date = request.args.get("date")
    data = load_data()
    if date:
        return jsonify(data.get(date, {}))
    return jsonify(data)


@app.route("/api/attendance", methods=["POST"])
def api_save_attendance():
    """
    Body JSON:
    {
      "date": "2026-10-12",
      "type": "nlss" | "mana" | "chakki" | "jondo",
      "records": { "1": {"status": "ok", "note": "..."}, ... }
    }
    """
    payload = request.get_json(force=True)
    date = payload.get("date")
    atype = payload.get("type")
    records = payload.get("records", {})

    if not date or not atype:
        return jsonify({"ok": False, "error": "Thiếu date hoặc type"}), 400
    if atype not in ("nlss", "mana", "chakki", "jondo"):
        return jsonify({"ok": False, "error": "type không hợp lệ"}), 400

    def update(data):
        data.setdefault(date, {})[atype] = records

    update_data(update)
    return jsonify({"ok": True, "message": f"Đã lưu {atype.upper()} ngày {date}"})


@app.route("/api/finalize-day", methods=["POST"])
def api_finalize_day():
    """Chốt ảnh chụp chính thức của bốn mục điểm danh trong ngày."""
    payload = request.get_json(force=True)
    date = payload.get("date")
    if not date:
        return jsonify({"ok": False, "error": "Thiếu date"}), 400

    def update(data):
        day = data.setdefault(date, {})
        day["_official_attendance"] = {
            t: day.get(t, {}) for t in ("nlss", "mana", "chakki", "jondo")
        }
        day["_finalized_at"] = datetime.now().isoformat(timespec="seconds")

    update_data(update)
    return jsonify({"ok": True, "message": f"Đã chốt kết quả chính thức ngày {date}"})


@app.route("/api/reflection", methods=["POST"])
def api_save_reflection():
    """
    Body:
    {
      "date": "...",
      "topic": "...",
      "leader_note": "...",
      "notes": { "1": "nội dung...", ... }
    }
    """
    payload = request.get_json(force=True)
    date = payload.get("date")
    if not date:
        return jsonify({"ok": False, "error": "Thiếu date"}), 400

    def update(data):
        data.setdefault(date, {})["reflection"] = {
            "topic": payload.get("topic", ""),
            "leader_note": payload.get("leader_note", ""),
            "notes": payload.get("notes", {}),
        }

    update_data(update)
    return jsonify({"ok": True, "message": "Đã lưu suy ngẫm"})


@app.route("/api/weekly", methods=["POST"])
def api_save_weekly():
    """Lưu báo cáo tuần"""
    payload = request.get_json(force=True)
    week_key = payload.get("week_key")  # ví dụ "2026-W41"
    if not week_key:
        return jsonify({"ok": False, "error": "Thiếu week_key"}), 400

    def update(data):
        data.setdefault("weekly_reports", {})[week_key] = payload

    update_data(update)
    return jsonify({"ok": True, "message": "Đã lưu báo cáo tuần"})


@app.route("/api/availability", methods=["GET", "POST"])
def api_availability():
    """Đọc hoặc lưu lịch rảnh theo tuần cho từng thành viên."""
    if request.method == "GET":
        week_key = request.args.get("week_key", "")
        if not week_key:
            return jsonify({"ok": False, "error": "Thiếu week_key"}), 400
        data = load_data()
        return jsonify(data.get("availability_weeks", {}).get(week_key, {}))

    payload = request.get_json(force=True)
    week_key = payload.get("week_key", "")
    member_id = str(payload.get("member_id", ""))
    slots = payload.get("slots", [])
    valid_ids = {str(member["id"]) for member in MEMBERS}
    if not week_key or len(week_key) != 10:
        return jsonify({"ok": False, "error": "week_key không hợp lệ"}), 400
    if member_id not in valid_ids:
        return jsonify({"ok": False, "error": "Thành viên không hợp lệ"}), 400
    valid_slots = {f"{day}-{period}" for day in range(1, 8) for period in ("morning", "afternoon", "evening")}
    if not isinstance(slots, list) or any(
        not isinstance(slot, str) or slot not in valid_slots for slot in slots
    ):
        return jsonify({"ok": False, "error": "Danh sách khung giờ không hợp lệ"}), 400

    def update(data):
        week = data.setdefault("availability_weeks", {}).setdefault(week_key, {})
        week[member_id] = {
            "slots": sorted(set(slots)),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

    update_data(update)
    return jsonify({"ok": True, "message": "Đã gửi lịch rảnh"})


@app.route("/api/stats")
def api_stats():
    """Thống kê theo ngày hoặc khoảng ngày"""
    date = request.args.get("date")
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    data = load_data()
    result = {"members": MEMBERS}

    ACTIVITY_TYPES = ["nlss", "mana", "chakki", "jondo"]

    if date:
        day = data.get(date, {})
        official_day = day.get("_official_attendance", day)
        result["date"] = date
        result["day"] = {**day, **official_day}
        # Tính summary
        summary = {}
        for t in ACTIVITY_TYPES:
            records = official_day.get(t, {})
            done = sum(1 for v in records.values() if (isinstance(v, dict) and v.get("status") == "ok") or v == "ok")
            summary[t] = {"done": done, "total": len(MEMBERS)}
        result["summary"] = summary
        return jsonify(result)

    if from_date and to_date:
        # Thống kê khoảng
        stats = {m["id"]: {t: 0 for t in ACTIVITY_TYPES} for m in MEMBERS}
        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d")
        total_days = 0
        d = start
        while d <= end:
            key = d.strftime("%Y-%m-%d")
            total_days += 1
            day = data.get(key, {})
            official_day = day.get("_official_attendance", day)
            for m in MEMBERS:
                mid = str(m["id"])
                for t in ACTIVITY_TYPES:
                    rec = official_day.get(t, {}).get(mid) or official_day.get(t, {}).get(m["id"])
                    if rec:
                        status = rec.get("status") if isinstance(rec, dict) else rec
                        if status == "ok":
                            stats[m["id"]][t] += 1
            d += timedelta(days=1)

        result["from"] = from_date
        result["to"] = to_date
        result["total_days"] = total_days
        result["stats"] = stats
        return jsonify(result)

    return jsonify({"error": "Cần date hoặc from+to"}), 400


@app.route("/api/history")
def api_history():
    data = load_data()
    # Bỏ weekly_reports ra khỏi danh sách ngày
    dates = sorted(
        [k for k in data.keys() if k != "weekly_reports" and len(k) == 10],
        reverse=True,
    )
    history = []
    for d in dates[:60]:  # tối đa 60 ngày gần nhất
        day = data[d]
        display_day = day.get("_official_attendance", day)
        item = {"date": d}
        # Dữ liệu cũ được lưu bằng nút Lưu trước đây được xem là kết quả chính thức.
        item["finalized"] = "_official_attendance" in day or any(t in day for t in ("nlss", "mana", "chakki", "jondo"))
        for t in ["nlss", "mana", "chakki", "jondo"]:
            if t in display_day:
                records = display_day[t]
                done = sum(
                    1
                    for v in records.values()
                    if (isinstance(v, dict) and v.get("status") == "ok") or v == "ok"
                )
                item[t] = done
        if "reflection" in day:
            item["has_reflection"] = True
        history.append(item)
    return jsonify(history)


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """Xóa toàn bộ dữ liệu (cẩn thận!)"""
    def clear(data):
        data.clear()

    update_data(clear)
    return jsonify({"ok": True, "message": "Đã xóa toàn bộ dữ liệu"})


if __name__ == "__main__":
    print("=" * 50)
    print("  ĐL-T4 Dashboard đang chạy")
    print("  Mở trình duyệt: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
