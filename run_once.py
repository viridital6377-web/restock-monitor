"""
補貨/新品監控腳本（GitHub Actions 單次執行版本）
"""

import os
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ========== 設定區 ==========

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SEARCH_TARGETS = [
    {
        "platform": "momo",
        "url": "https://www.momoshop.com.tw/search/searchShop.jsp?keyword=戰鬥陀螺",
        "item_selector": "li.goodsItemLi",
        "link_selector": "a",
        "name_selector": "p.prdName",
    },
    {
        "platform": "pchome",
        "url": "https://ecshweb.pchome.com.tw/search/v3.3/all/results?q=beyblade",
        "item_selector": "li.c-listInfoGrid__item",
        "link_selector": "a",
        "name_selector": "div.c-prodInfoV2__title",
    },
]

KEYWORDS = ["戰鬥陀螺", "beyblade", "Beyblade", "BEYBLADE", "鋼彈"]
STATE_FILE = "seen_items.json"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
}

# 發送請求時帶入 headers
response = requests.get(url, headers=headers, timeout=10)


# ========== 核心邏輯 ==========

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[{now()}] 讀取狀態檔失敗，重置狀態: {e}")
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[{now()}] 未設定 Telegram Token 或 Chat ID，跳過發送")
        return

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

            # 自動補全相對網址 (例如 /items/123 -> https://domain.com/items/123)
            full_url = urljoin(target["url"], href)
            items.append({"name": name, "url": full_url})

    except Exception as e:
        print(f"[{now()}] 抓取 {target['platform']} 時發生錯誤: {e}")

    return items

def check_target(target: dict, state: dict):
    platform = target["platform"]
    seen = set(state.get(platform, []))

    items = fetch_items(target)
    print(f"[{now()}] {platform}: 抓到 {len(items)} 筆符合關鍵字的商品")

    new_items = [item for item in items if item["url"] not in seen]

    # 首次執行如果看到大量商品，預防洗版可斟酌（目前 logic 是全發）
    for item in new_items:
        send_telegram(
            f"🆕 新商品出現！\n平台：{platform}\n名稱：{item['name']}\n{item['url']}"
        )
        seen.add(item["url"])

    state[platform] = list(seen)
    return state

def main():
    state = load_state()
    print(f"[{now()}] 開始執行單次檢查...")

    for target in SEARCH_TARGETS:
        state = check_target(target, state)

    save_state(state)
    print(f"[{now()}] 檢查完成，已更新狀態檔。")

if __name__ == "__main__":
    main()
