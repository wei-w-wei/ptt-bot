import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

# ================= 1. 參數設定區 =================
BOARD = 'Lifeismoney'
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

HISTORY_FILE = 'ptt_history.txt'  
HEARTBEAT_FILE = 'ptt_heartbeat.txt' # 💡 新增：早安報的記憶檔
# ===============================================

def send_telegram_message(text):
    """將訊息發送到 Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': 'HTML'
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram 發送失敗：{e}")

def fetch_ptt_latest_articles(board):
    """抓取 PTT 最新文章並回傳列表"""
    url = f"https://www.ptt.cc/bbs/{board}/index.html"
    headers = {'User-Agent': 'Mozilla/5.0'}
    cookies = {'over18': '1'}
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        container = soup.find('div', class_='r-list-container')
        
        if container:
            for child in container.children:
                if child.name == 'div' and 'r-list-sep' in child.get('class', []):
                    break
                if child.name == 'div' and 'r-ent' in child.get('class', []):
                    title_tag = child.find('div', class_='title').find('a')
                    if title_tag:
                        title = title_tag.text
                        if "公告" not in title: 
                            link = "https://www.ptt.cc" + title_tag['href']
                            results.append({'title': title, 'link': link})
        return results
    except Exception as e:
        print(f"抓取失敗：{e}")
        return []

# ================= 程式執行起點 =================
if __name__ == "__main__":
    print("啟動雲端檢查任務...")
    
    # 💡 強制校正為台灣時間 (UTC+8)
    utc_now = datetime.now(timezone.utc)
    tw_now = utc_now.astimezone(timezone(timedelta(hours=8)))
    tw_date = tw_now.strftime("%Y-%m-%d") # 今天的日期，例如 2026-05-31
    tw_hour = tw_now.hour                 # 現在的小時
    
    # 1. 檢查是否需要發送「每日早安回報」
    # 設定在台灣時間早上 8 點之後的第一次執行發送
    if tw_hour >= 8:
        if os.path.exists(HEARTBEAT_FILE):
            with open(HEARTBEAT_FILE, 'r', encoding='utf-8') as f:
                last_heartbeat_date = f.read().strip()
        else:
            last_heartbeat_date = ""
        
        # 如果今天還沒發送過早安回報
        if last_heartbeat_date != tw_date:
            morning_msg = (
                "🌅 <b>早安！系統定期巡邏回報</b>\n"
                "省錢板監控機器人目前在雲端穩定運作中，開啟新一天的守望！"
            )
            send_telegram_message(morning_msg)
            print("✅ 成功發送每日早安回報！")
            
            # 記住今天已經發過了
            with open(HEARTBEAT_FILE, 'w', encoding='utf-8') as f:
                f.write(tw_date)

    # 2. 處理常規的 PTT 新文章檢查
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, 'w').close()

    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        notified_links = f.read().splitlines()
        
    current_articles = fetch_ptt_latest_articles(BOARD)
    new_articles = []
    for art in current_articles:
        if art['link'] not in notified_links:
            new_articles.append(art)
            
    if new_articles:
        message_body = f"<b>💰 PTT 省錢板有新情報！</b>\n\n"
        for art in new_articles:
            message_body += f"📌 <a href='{art['link']}'>{art['title']}</a>\n\n"
            notified_links.append(art['link']) 
            
        send_telegram_message(message_body)
        print(f"✅ 成功發送 {len(new_articles)} 篇新文章通知！")
        
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(notified_links[-100:]))
    else:
        print("目前沒有新文章，任務結束。")