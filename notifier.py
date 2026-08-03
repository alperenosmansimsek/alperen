# notifier.py
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_session_start_divider(self):
        """Program her çalıştığında en başta ayrım çizgisi atar."""
        divider_message = "------------------------------\n🚀 **YENİ İŞ ARAMA VE ANALİZ SEANSI BAŞLADI**\n------------------------------"
        payload = {
            "chat_id": self.chat_id,
            "text": divider_message,
            "parse_mode": "Markdown"
        }
        try:
            requests.post(self.api_url, json=payload, timeout=10)
        except Exception as e:
            print(f"⚠️ Seans çizgisi atılamadı: {e}")

    def send_job_notification(self, job: dict, eval_result: dict):
        """Barajı geçen ilanlar için Telegram bildirimi yollar."""
        score = eval_result.get("match_score", 0)
        cand_summary = eval_result.get("candidate_summary", "Relevant background matches core needs.")
        reason = eval_result.get("reason", "")
        focus = eval_result.get("recommended_focus", "")

        message = f"""
📌 **Role:** {job['title']}
🏢 **Company:** {job['company']}
📍 **Location:** {job['city']}
📊 **Match Score:** `{score}%`

👤 **Candidate Fit Summary:**
_{cand_summary}_

📝 **Acceptance Analysis:**
{reason}

🎯 **CV / Application Focus:**
• {focus}

🔗 **Apply Here:**
{job['url']}
"""

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }

        try:
            res = requests.post(self.api_url, json=payload, timeout=10)
            if res.status_code == 200:
                print(f"📩 Telegram bildirimi gönderildi: {job['title']} @ {job['company']}")
            else:
                print(f"⚠️ Telegram Error: {res.text}")
        except Exception as e:
            print(f"❌ Bildirim hatası: {e}")