import os
import requests

# 讀取 GitHub Actions Secrets 設定的環境變數
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("=== DEBUG START ===")
print(f"Token 是否存在: {bool(BOT_TOKEN)}")
print(f"Chat ID 是否存在: {bool(CHAT_ID)}")

if not BOT_TOKEN or not CHAT_ID:
    print("錯誤：找不到 Telegram Token 或 Chat ID！請檢查 Secrets 設定。")
    exit(1)

# 發送測試訊息至 Telegram
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "🎉 測試訊息：GitHub Actions 監控腳本連線成功！"
}

try:
    response = requests.post(url, json=payload, timeout=10)
    res_data = response.json()
    print("Telegram API 回傳結果:", res_data)
    
    if res_data.get("ok"):
        print("訊息發送成功！正在建立 seen_items.json...")
        # 建立記錄檔供後續 Auto Commit 測試
        with open("seen_items.json", "w", encoding="utf-8") as f:
            f.write("{}")
        print("seen_items.json 已成功建立！")
    else:
        print("Telegram 發送失敗，錯誤原因:", res_data.get("description"))

except Exception as e:
    print("請求發生異常:", str(e))

print("=== DEBUG END ===")
