"""
洗車スケジュール共有 - 予約の登録/取消をGitHubに保存するAPI (Vercel Serverless)
GitHubトークンはこのサーバー側だけが保持し、フロントエンドには一切渡さない
"""

import os
import re
import json
import base64
import datetime
from http.server import BaseHTTPRequestHandler

import requests

GITHUB_TOKEN = os.environ.get("WASH_SCHEDULE_GITHUB_TOKEN", "")
REPO = "muuuuum/ai-news"
FILE_PATH = "data/wash-schedule.json"
CONTENTS_API = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(11, 18) for m in (0, 30)]
NO_RE = re.compile(r"^\d{4}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MAX_RETRIES = 3


def gh_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def fetch_current():
    resp = requests.get(CONTENTS_API, headers=gh_headers(), timeout=10)
    resp.raise_for_status()
    data = resp.json()
    content = json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    content.setdefault("bookings", {})
    return content, data["sha"]


def push_current(content, sha):
    payload = json.dumps(content, ensure_ascii=False, indent=2)
    body = {
        "message": "update wash schedule",
        "content": base64.b64encode(payload.encode("utf-8")).decode("ascii"),
        "sha": sha,
    }
    resp = requests.put(CONTENTS_API, headers=gh_headers(), json=body, timeout=10)
    return resp


def mutate_with_retry(mutate_fn):
    """現在の内容を取得→mutate_fnで書き換え→保存。sha競合時は再試行する。
    戻り値: (ok, status_code, result_dict)"""
    last_error = None
    for _ in range(MAX_RETRIES):
        content, sha = fetch_current()
        ok, status, result = mutate_fn(content)
        if not ok:
            return ok, status, result
        resp = push_current(content, sha)
        if resp.ok:
            return True, 200, {"ok": True, "bookings": content["bookings"]}
        if resp.status_code == 409:
            last_error = "他の予約と競合しました。再試行します。"
            continue
        return False, 502, {"error": f"GitHub保存に失敗しました: {resp.status_code}"}
    return False, 409, {"error": last_error or "競合が解消できませんでした。もう一度お試しください。"}


def validate_slot(date, time):
    return bool(DATE_RE.match(date or "")) and time in TIME_SLOTS


class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def do_GET(self):
        if not GITHUB_TOKEN:
            self._send(500, {"error": "サーバーにGitHubトークンが設定されていません"})
            return
        try:
            content, _ = fetch_current()
            self._send(200, content)
        except Exception as e:
            self._send(502, {"error": str(e)})

    def do_POST(self):
        if not GITHUB_TOKEN:
            self._send(500, {"error": "サーバーにGitHubトークンが設定されていません"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except json.JSONDecodeError:
            self._send(400, {"error": "リクエストの形式が不正です"})
            return

        action = payload.get("action")
        date = str(payload.get("date", ""))
        time = str(payload.get("time", ""))

        if not validate_slot(date, time):
            self._send(400, {"error": "日付または時間が不正です"})
            return

        key = f"{date}_{time}"

        if action == "book":
            no = str(payload.get("no", "")).strip()
            name = str(payload.get("name", "")).strip()[:30]
            if not NO_RE.match(no):
                self._send(400, {"error": "No.は数字4桁で入力してください"})
                return
            if not name:
                self._send(400, {"error": "所有者名を入力してください"})
                return

            def do_book(content):
                if key in content["bookings"]:
                    return False, 409, {"error": "その時間は既に予約済みです", "bookings": content["bookings"]}
                content["bookings"][key] = {
                    "no": no,
                    "name": name,
                    "date": date,
                    "time": time,
                    "createdAt": datetime.datetime.utcnow().isoformat() + "Z",
                }
                content["syncedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
                return True, 200, {}

            try:
                ok, status, result = mutate_with_retry(do_book)
            except Exception as e:
                self._send(502, {"error": str(e)})
                return
            self._send(status, result)

        elif action == "cancel":
            def do_cancel(content):
                content["bookings"].pop(key, None)
                content["syncedAt"] = datetime.datetime.utcnow().isoformat() + "Z"
                return True, 200, {}

            try:
                ok, status, result = mutate_with_retry(do_cancel)
            except Exception as e:
                self._send(502, {"error": str(e)})
                return
            self._send(status, result)

        else:
            self._send(400, {"error": "不明な操作です"})
