import html
import time
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

class TelegramNotifier:
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def _send_payload(self, text: str, retries: int = 3) -> bool:
        """Rate limit (429) korumalı ve güvenli mesaj gönderici."""
        payload = {
            "chat_id": self.chat_id,
            "text": text[:4000],  # Telegram 4096 sınırını aşmaması için güvenlik marjı
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        for attempt in range(retries):
            try:
                res = requests.post(self.api_url, json=payload, timeout=12)
                if res.status_code == 200:
                    return True
                
                # Telegram Rate Limit Kontrolü
                if res.status_code == 429:
                    retry_after = res.json().get("parameters", {}).get("retry_after", 3)
                    print(f"      ⏳ Telegram Rate Limit: {retry_after} saniye bekleniyor...")
                    time.sleep(retry_after + 0.5)
                    continue

                print(f"      ⚠️ Telegram API Hatası ({res.status_code}): {res.text}")
                return False

            except Exception as e:
                print(f"      ⚠️️ Telegram bağlantı hatası (Deneme {attempt+1}/{retries}): {e}")
                time.sleep(1.5)

        return False

    def send_session_start_divider(self):
        """Her tarama seansı başladığında Telegram'a bildirim atar."""
        divider_message = (
            "------------------------------\n"
            "🚀 <b>YENİ İŞ ARAMA VE ANALİZ SEANSI BAŞLADI</b>\n"
            "------------------------------"
        )
        self._send_payload(divider_message)

    def send_job_notification(self, job: dict, eval_result: dict) -> bool:
        """Kriterleri ve barajı geçen ilanlar için şık Telegram kartı oluşturur."""
        score = eval_result.get("match_score", 0)
        cand_summary = html.escape(str(eval_result.get("candidate_summary", "Profille güçlü örtüşme.")))
        reason = html.escape(str(eval_result.get("reason", "Pozisyon yetkinliklerle uyuşuyor.")))
        focus = html.escape(str(eval_result.get("recommended_focus", "İlgili tecrübeleri öne çıkarın.")))
        
        title = html.escape(str(job.get('title', 'Unknown Role')).strip())
        company = html.escape(str(job.get('company', 'Unknown Company')).strip())
        city = html.escape(str(job.get('city', 'Warsaw / Remote')).strip())
        url = job.get('url', '').strip()

        message = (
            f"📌 <b>Role:</b> {title}\n"
            f"🏢 <b>Company:</b> {company}\n"
            f"📍 <b>Location:</b> {city}\n"
            f"📊 <b>Match Score:</b> <code>%{score}</code>\n\n"
            f"👤 <b>Candidate Fit Summary:</b>\n"
            f"<i>{cand_summary}</i>\n\n"
            f"📝 <b>Acceptance Analysis:</b>\n"
            f"{reason}\n\n"
            f"🎯 <b>CV / Application Focus:</b>\n"
            f"• {focus}\n\n"
            f"🔗 <b>Apply Here:</b>\n"
            f"{url}"
        )

        success = self._send_payload(message)
        if success:
            print(f"   📩 Telegram bildirimi gönderildi: {title} @ {company}")
        return success
