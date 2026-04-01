# yumo-trend-tracker

瑀墨塗料趨勢追蹤器 — 每日自動搜尋裝潢/油漆相關高流量短影音，推播至 Telegram。

## 功能

- YouTube Data API v3 搜尋最近 7 天短影音
- 10 組關鍵字（中英文），每組取 3 部，去重後按觀看數排序取 Top 10
- Telegram Bot 推播每日趨勢日報
- GitHub Actions 每天台灣時間 08:00 自動執行

## 設定

1. 在 GitHub repo Settings → Secrets 加入：
   - `YOUTUBE_API_KEY` — Google Cloud Console 取得
   - `TELEGRAM_BOT_TOKEN` — @BotFather 取得
   - `TELEGRAM_CHAT_ID` — 目標聊天室 ID

2. 啟用 GitHub Actions（預設已啟用）

## 本地測試

```bash
cp .env.example .env
# 填入真實金鑰
export $(cat .env | xargs)
pip install -r requirements.txt
python tracker.py
```
