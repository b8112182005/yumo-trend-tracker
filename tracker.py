"""瑀墨趨勢追蹤器 — 每日搜尋裝潢/油漆相關高流量短影音，推播至 Telegram"""
import os
import json
import httpx
from datetime import datetime, timedelta, timezone
from pathlib import Path

YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

KEYWORDS = [
    "油漆DIY", "刷漆教學", "牆壁改造", "乳膠漆", "裝潢油漆",
    "房間改造", "wall painting", "room makeover paint",
    "paint transformation", "塗料推薦",
]

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

TW = timezone(timedelta(hours=8))
HISTORY_FILE = Path(__file__).parent / "sent_history.json"
DEDUP_DAYS = 3


def load_history() -> dict:
    """載入已發送紀錄，格式: {video_id: "2026-04-02", ...}"""
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def save_history(history: dict):
    """儲存已發送紀錄，清除超過 DEDUP_DAYS 的舊紀錄"""
    cutoff = (datetime.now(TW) - timedelta(days=DEDUP_DAYS)).strftime("%Y-%m-%d")
    cleaned = {vid: date for vid, date in history.items() if date >= cutoff}
    HISTORY_FILE.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")


def search_videos(client: httpx.Client, keyword: str, published_after: str) -> list[dict]:
    """搜尋 YouTube 短影音，回傳最多 3 部"""
    resp = client.get(YOUTUBE_SEARCH_URL, params={
        "part": "snippet",
        "q": keyword,
        "type": "video",
        "videoDuration": "short",
        "order": "viewCount",
        "regionCode": "TW",
        "relevanceLanguage": "zh-Hant",
        "publishedAfter": published_after,
        "maxResults": 3,
        "key": YOUTUBE_API_KEY,
    })
    resp.raise_for_status()
    results = []
    for item in resp.json().get("items", []):
        results.append({
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "keyword": keyword,
        })
    return results


def get_view_counts(client: httpx.Client, video_ids: list[str]) -> dict[str, int]:
    """批次取得觀看數"""
    if not video_ids:
        return {}
    resp = client.get(YOUTUBE_VIDEOS_URL, params={
        "part": "statistics",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    })
    resp.raise_for_status()
    counts = {}
    for item in resp.json().get("items", []):
        counts[item["id"]] = int(item["statistics"].get("viewCount", 0))
    return counts


def build_message(top_videos: list[dict], today: str) -> str:
    """組裝 Telegram 訊息"""
    lines = [
        f"🎨 瑀墨趨勢日報 — {today}",
        "=" * 30,
        "",
    ]
    for i, v in enumerate(top_videos, 1):
        views = f"{v['views']:,}"
        lines.append(f"📹 #{i} {v['title']}")
        lines.append(f"   👤 {v['channel']}")
        lines.append(f"   👁 {views} 次觀看")
        lines.append(f"   🔑 關鍵字：{v['keyword']}")
        lines.append(f"   🔗 https://youtube.com/shorts/{v['video_id']}")
        lines.append("")

    lines.append("─" * 30)
    lines.append("📊 TikTok 趨勢手動查看：")
    lines.append("https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/zh-Hant")
    return "\n".join(lines)


def send_telegram(message: str):
    """推播至 Telegram"""
    with httpx.Client() as client:
        resp = client.post(TELEGRAM_URL, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        })
        resp.raise_for_status()


def main():
    now = datetime.now(TW)
    today = now.strftime("%Y/%m/%d")
    today_key = now.strftime("%Y-%m-%d")
    published_after = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    history = load_history()

    # 搜尋所有關鍵字
    all_videos: dict[str, dict] = {}  # video_id → info
    with httpx.Client(timeout=30) as client:
        for kw in KEYWORDS:
            for v in search_videos(client, kw, published_after):
                vid = v["video_id"]
                if vid not in all_videos and vid not in history:
                    all_videos[vid] = v

        # 批次取得觀看數
        view_counts = get_view_counts(client, list(all_videos.keys()))

    # 補上觀看數，按觀看數排序取 Top 10
    for vid, info in all_videos.items():
        info["views"] = view_counts.get(vid, 0)

    top10 = sorted(all_videos.values(), key=lambda x: x["views"], reverse=True)[:10]

    if not top10:
        send_telegram(f"🎨 瑀墨趨勢日報 — {today}\n\n⚠️ 今日無新影片（近 3 天已推播的不重複顯示）")
        return

    # 記錄本次發送的 video_id
    for v in top10:
        history[v["video_id"]] = today_key
    save_history(history)

    message = build_message(top10, today)
    send_telegram(message)
    print(f"✅ 已推播 {len(top10)} 部影片（已排除 {len(history) - len(top10)} 部近期重複）")


if __name__ == "__main__":
    main()
