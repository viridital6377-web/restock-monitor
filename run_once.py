import os
import json
import urllib.parse
import requests

# 1. Telegram 設定
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 2. 監控與過濾設定
KEYWORDS = ["戰鬥陀螺", "BX-", "UX-"]  # 只要包含這些關鍵字即可
ALLOWED_STORES = [
    "Funbox", "funbox", 
    "玩具E哥", 
    "誠品", "eslite", 
    "momo", "MOMO",
    "PChome", "pchome", "24h",
    "麗嬰國際"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
}

SEEN_FILE = "seen_items.json"

def load_seen_items():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_seen_items(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=2)

def is_trusted_store(item_title, seller_name=""):
    """檢查是否來自白名單指定通路"""
    full_text = f"{item_title} {seller_name}".lower()
    return any(store.lower() in full_text for store in ALLOWED_STORES)

def is_target_keyword(item_title):
    """檢查標題是否包含目標關鍵字"""
    return any(kw.lower() in item_title.lower() for kw in KEYWORDS)

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID:
        print("未設定 Telegram 憑證，無法發送訊息。")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"發送 Telegram 訊息失敗: {e}")

def check_pchome():
    results = []
    query = urllib.parse.quote("戰鬥陀螺")
    url = f"https://ecshweb.pchome.com.tw/search/v3.3/all/results?q={query}&page=1&sort=rnk/dc"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            for prod in data.get("prods", []):
                name = prod.get("name", "")
                price = prod.get("price", 0)
                
                # 確保正確取得 Id 欄位（PChome API key 通常是 Id 或 IdStr）
                prod_id = str(prod.get("Id", prod.get("id", "")))
                
                # 只有拿到 ID 時才拼接完整網址（標準 24h 網址）
                if prod_id:
                    prod_url = f"https://24h.pchome.com.tw/prod/{prod_id}"
                else:
                    continue
                
                if is_target_keyword(name) and is_trusted_store(name, "PChome 24h"):
                    results.append({
                        "id": f"pchome_{prod_id}",
                        "title": name,
                        "price": price,
                        "link": prod_url,
                        "store": "PChome 24h"
                    })
    except Exception as e:
        print(f"抓取 PChome 失敗: {e}")
    return results

def check_momo():
    results = []
    query = urllib.parse.quote("戰鬥陀螺")
    url = f"https://m.momoshop.com.tw/mosearch/{query}.html"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        # MOMO 搜尋頁解析邏輯，若阻擋則回傳空清單保護程式不崩潰
        if res.status_code == 200:
            pass 
    except Exception as e:
        print(f"抓取 momo 失敗: {e}")
    return results

def main():
    print(f"[{os.popen('date').read().strip()}] 開始執行戰鬥陀螺精準監控...")
    seen_items = load_seen_items()
    
    all_found = []
    all_found.extend(check_pchome())
    all_found.extend(check_momo())
    
    new_items = []
    for item in all_found:
        item_id = item["id"]
        if item_id not in seen_items:
            seen_items[item_id] = item["title"]
            new_items.append(item)
            
    if new_items:
        msg = f"🚨 <b>戰鬥陀螺指定通路補貨通知！</b> (共 {len(new_items)} 筆)\n\n"
        for item in new_items:
            msg += f"📦 <b>{item['title']}</b>\n"
            msg += f"🏪 通路：{item['store']}\n"
            msg += f"💰 價格：${item['price']}\n"
            msg += f"🔗 <a href='{item['link']}'>點此前往購買</a>\n\n"
        
        send_telegram(msg)
        print(f"已發送 {len(new_items)} 筆新商品通知至 Telegram。")
    else:
        print("未發現指定白名單通路的全新商品。")
        
    save_seen_items(seen_items)
    print("檢查完成，已更新 status 紀錄。")

if __name__ == "__main__":
    main()
