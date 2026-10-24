
import os
import json
import hashlib
import urllib.request
import urllib.error
import urllib.parse
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# 確認用の既存イベント
SEED_EVENTS = [
    {
        "title": "消防ひろば2026 キッチンカー出店",
        "area": "三河",
        "event_type": "イベント",
        "event_date": "2026-11-21",
        "deadline": None,
        "fee": "無料",
        "status": "要確認",
        "food_truck_allowed": "可",
        "source_name": "蒲郡市消防本部",
        "source_url": "https://www.city.gamagori.lg.jp/site/shobo/shobohiroba-kitchencar2026.html",
        "summary": "キッチンカー募集候補。受付状況と条件は主催者へ確認してください。",
    }
]

# 募集情報を探す入口
LISTING_URLS = [    "https://gyosei-shutten.jp/area/aichi/",
    "https://www.pref.aichi.jp/soshiki/gorin/2026heisai.html",
    "https://www.city.seto.aichi.jp/docs/2023/08/04/008533656/008533656.html",
    "https://www.city.chiryu.aichi.jp/boshu/other/1661318839621.html",
                    "https://event-shutten-navi.com/",
               ]

KEYWORDS = (
    "キッチンカー",
    "出店募集",
    "出店者募集",
    "出店者を募集",
    "移動販売",
    "マルシェ",
    "フードトラック",
)

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self.href = dict(attrs).get("href")
            self.parts = []

    def handle_data(self, data):
        if self.href is not None:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.href is not None:
            label = " ".join(self.parts).strip()
            self.links.append((self.href, label))
            self.href = None
            self.parts = []

def request(url, method="GET", body=None, extra=None):
    headers = {
        "User-Agent": "TakoshinShuttenNavi/1.0 (GitHub Actions)",
        "apikey": SUPABASE_KEY,
    }
    if extra:
        headers.update(extra)

    req = urllib.request.Request(
        url, data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {detail}") from e

def make_key(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]

def discover(url):
    try:
        _, raw = request(url)
        parser = LinkParser()
        parser.feed(raw.decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"取得失敗: {url} / {e}")
        return []

    results = []
    seen = set()
    host = urlparse(url).netloc

    for href, label in parser.links:
        title = re.sub(r"\s+", " ", label).strip()
        if not title or len(title) < 4:
            continue

        if not any(word in title for word in KEYWORDS):
            continue

        link = urljoin(url, href)
        parsed = urlparse(link)

        if parsed.scheme != "https" or parsed.netloc != host:
            continue
        if link in seen:
            continue

        seen.add(link)
        results.append({
            "title": title[:250],
            "area": "愛知県内・地域不明",
            "event_type": "イベント",
            "event_date": None,
            "deadline": None,
            "fee": "要確認",
            "status": "要確認",
            "food_truck_allowed": "要確認",
            "source_name": "愛知県内の出店募集情報（要確認）",
            "source_url": link,
            "summary": "自動検出した募集候補です。応募期限・出店料・食品出店条件をリンク先の主催者公式情報で確認してください。"
        })

    print(f"候補検出: {len(results)}件 / {url}")
    return results

def save_event(event):
    event = dict(event)
    event["dedupe_key"] = make_key(event["source_url"])

    base = f"{SUPABASE_URL}/rest/v1/events"
    key = urllib.parse.quote(event["dedupe_key"], safe="")
    check_url = (
        f"{base}?dedupe_key=eq.{key}&select=dedupe_key"
    )

    _, raw = request(check_url)
    existing = json.loads(raw.decode("utf-8"))

    if existing:
        print("登録済み:", event["title"])
        return

    payload = json.dumps(
        event, ensure_ascii=False
    ).encode("utf-8")

    status, _ = request(
        base,
        method="POST",
        body=payload,
        extra={
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )
    print("登録成功:", event["title"], status)

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "GitHub SecretsのSUPABASE_URLとSUPABASE_KEYを確認してください"
        )

    for event in SEED_EVENTS:
        try:
            save_event(event)
        except Exception as e:
            print("既存イベント登録エラー:", e)

    for url in LISTING_URLS:
        try:
            for event in discover(url):
                try:
                    save_event(event)
                except Exception as e:
                    print("候補登録エラー:", e)
        except Exception as e:
            print("情報源の取得失敗:", url, e)

if __name__ == "__main__":
    main()
