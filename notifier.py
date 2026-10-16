import html
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send_session_start_divider(self):
        """Program her çalıştığında en başta ayrım çizgisi atar."""
        divider_message = "------------------------------\n🚀 <b>YENİ İŞ ARAMA VE ANALİZ SEANSI BAŞLADI</b>\n------------------------------"
        payload = {
            "chat_id": self.chat_id,
            "text": divider_message,
            "parse_mode": "HTML"
        }
        try:
            requests.post(self.api_url, json=payload, timeout=10)
        except Exception as e:
            print(f"⚠️ Seans çizgisi atılamadı: {e}")

    def send_job_notification(self, job: dict, eval_result: dict):
        """Barajı geçen ilanlar için Telegram bildirimi yollar."""
        score = eval_result.get("match_score", 0)
        cand_summary = html.escape(eval_result.get("candidate_summary", "Relevant background matches core needs."))
        reason = html.escape(eval_result.get("reason", ""))
        focus = html.escape(eval_result.get("recommended_focus", ""))
        
        title = html.escape(str(job.get('title', 'Unknown Role')))
        company = html.escape(str(job.get('company', 'Unknown Company')))
        city = html.escape(str(job.get('city', 'Warsaw / Remote')))
        url = job.get('url', '')

        message = f"""📌 <b>Role:</b> {title}
🏢 <b>Company:</b> {company}
📍 <b>Location:</b> {city}
📊 <b>Match Score:</b> <code>%{score}</code>

👤 <b>Candidate Fit Summary:</b>
<i>{cand_summary}</i>

📝 <b>Acceptance Analysis:</b>
{reason}

🎯 <b>CV / Application Focus:</b>
• {focus}

🔗 <b>Apply Here:</b>
{url}"""

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            res = requests.post(self.api_url, json=payload, timeout=10)
            if res.status_code == 200:
                print(f"   📩 Telegram bildirimi gönderildi: {title} @ {company}")
            else:
                print(f"   ⚠️ Telegram Error ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"   ❌ Bildirim hatası: {e}")
