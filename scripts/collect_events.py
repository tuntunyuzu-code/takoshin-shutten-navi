
import os
import json
import hashlib
import urllib.request
import urllib.error
import urllib.parse
from html.parser import HTMLParser

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

SOURCES = [
    {
        "title": "消防ひろば2026 キッチンカー出店",
        "area": "三河",
        "event_type": "イベント",
        "event_date": "2026-11-21",
        "deadline": "2026-10-31",
        "fee": "無料",
        "status": "要確認",
        "food_truck_allowed": "可",
        "source_name": "蒲郡市消防本部",
        "source_url": "https://www.city.gamagori.lg.jp/site/shobo/shobohiroba-kitchencar2026.html",
        "summary": "キッチンカー募集。募集数は5店舗程度。応募前に受付状況と条件を主催者へ確認してください。",
        "required_text": "消防ひろば2026",
    }
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def http_request(url, method="GET", headers=None, body=None):
    req = urllib.request.Request(
        url,
        data=body,
        headers=headers or {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.status, response.read()


def headers(extra=None):
    result = {
        "apikey": SUPABASE_KEY,
    }
    if extra:
        result.update(extra)
    return result


def collect(source):
    event = {
        key: value
        for key, value in source.items()
        if key != "required_text"
    }

    event["deadline"] = ""

    event["dedupe_key"] = hashlib.sha256(
        source["source_url"].encode("utf-8")
    ).hexdigest()[:32]


    return event


def save_event(event):
    base = f"{SUPABASE_URL}/rest/v1/events"
    key = urllib.parse.quote(event["dedupe_key"], safe="")
    check_url = (
        f"{base}?dedupe_key=eq.{key}&select=dedupe_key"
    )

    _, raw = http_request(check_url, headers=headers())
    existing = json.loads(raw.decode("utf-8"))

    if existing:
        print("登録済み:", event["title"])
        return

    payload = json.dumps(
        event, ensure_ascii=False
    ).encode("utf-8")

    status, _ = http_request(
        base,
        method="POST",
        headers=headers({
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }),
        body=payload,
    )
    print("Supabase登録:", event["title"], status)


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL または SUPABASE_KEY が未設定です"
        )

    for source in SOURCES:
        event = collect(source)
        if event:
            save_event(event)


if __name__ == "__main__":
    main()
