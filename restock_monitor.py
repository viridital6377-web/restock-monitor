"""
補貨/新品監控腳本骨架（搜尋結果頁版本）
用途：定期抓某平台「戰鬥陀螺」/ "beyblade" 的搜尋結果頁，
     偵測到「之前沒看過的新商品」就透過 Telegram 通知自己。
"""

import requests
import time
import random
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup

# ========== 設定區 ==========

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "你的_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "你的_CHAT_ID")

# 要監控的搜尋結果頁清單
# 每個平台的搜尋網址格式不同，自己先在瀏覽器打「戰鬥陀螺」搜尋，
# 把網址列的網址複製過來（通常會有 keyword= 之類的參數）
SEARCH_TARGETS = [
    {
        "platform": "momo",
        "url": "https://www.momoshop.com.tw/search/searchShop.jsp?keyword=戰鬥陀螺",
        # 商品項目在頁面上的 CSS selector，要自己打開瀏覽器「檢查元素」找
        # 通常一個商品卡片會是 <li> 或 <div class="...">，裡面包一個 <a>
        "item_selector": "li.goodsItemLi",       # ← 依實際頁面調整
        "link_selector": "a",                     # 商品卡片裡的連結
        "name_selector": "p.prdName",             # 商品名稱
    },
    {
        "platform": "pchome",
        "url": "https://ecshweb.pchome.com.tw/search/v3.3/all/results?q=beyblade",
        "item_selector": "li.c-listInfoGrid__item",  # ← 依實際頁面調整
        "link_selector": "a",
        "name_selector": "div.c-prodInfoV2__title",
    },
]

# 用來過濾：商品名稱要包含這些關鍵字之一，才算符合
KEYWORDS = ["戰鬥陀螺", "beyblade", "Beyblade", "BEYBLADE"]

STATE_FILE = "seen_items.json"

CHECK_INTERVAL_MIN = 300
CHECK_INTERVAL_MAX = 600

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
}

# ========== 核心邏輯 ==========

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}  # { platform: [已看過的商品連結, ...] }

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[{now()}] Telegram 發送失敗: {e}")

def matches_keyword(name: str) -> bool:
    return any(kw.lower() in name.lower() for kw in KEYWORDS)

def fetch_items(target: dict) -> list:
    """
    回傳這個搜尋頁目前抓到的商品清單: [{"name": ..., "url": ...}, ...]
    """
    items = []
    try:
        resp = requests.get(target["url"], headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        cards = soup.select(target["item_selector"])
        for card in cards:
            link_tag = card.select_one(target["link_selector"])
            name_tag = card.select_one(target["name_selector"])
            if not link_tag or not name_tag:
                continue

            href = link_tag.get("href", "").strip()
            name = name_tag.get_text(strip=True)

            if not href or not name:
                continue
            if not matches_keyword(name):
                continue

            items.append({"name": name, "url": href})

    except Exception as e:
        print(f"[{now()}] 抓取 {target['platform']} 時發生錯誤: {e}")

    return items

def check_target(target: dict, state: dict):
    platform = target["platform"]
    seen = set(state.get(platform, []))

    items = fetch_items(target)
    print(f"[{now()}] {platform}: 抓到 {len(items)} 筆符合關鍵字的商品")

    new_items = [item for item in items if item["url"] not in seen]

    for item in new_items:
        send_telegram(
            f"🆕 新商品出現！\n平台：{platform}\n名稱：{item['name']}\n{item['url']}"
        )
        seen.add(item["url"])

    state[platform] = list(seen)
    return state

def run_once(state: dict):
    for target in SEARCH_TARGETS:
        state = check_target(target, state)
        time.sleep(random.uniform(1, 3))
    return state

def main():
    state = load_state()
    print(f"[{now()}] 監控啟動，追蹤 {len(SEARCH_TARGETS)} 個搜尋頁")

    while True:
        state = run_once(state)
        save_state(state)

        wait = random.uniform(CHECK_INTERVAL_MIN, CHECK_INTERVAL_MAX)
        print(f"[{now()}] 休息 {wait:.0f} 秒後再檢查...")
        time.sleep(wait)

if __name__ == "__main__":
    main()
