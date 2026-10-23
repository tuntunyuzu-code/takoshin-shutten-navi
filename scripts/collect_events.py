import os
import json
import urllib.request
import urllib.error

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "SUPABASE_URL または SUPABASE_KEY が未設定です"
        )

    # 接続確認のみ。まだデータの登録・変更は行いません。
    url = f"{SUPABASE_URL}/rest/v1/"
    request = urllib.request.Request(
        url,
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            print("Supabase接続確認:", response.status)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"Supabase接続エラー: HTTP {error.code}"
        ) from error

if __name__ == "__main__":
    main()
