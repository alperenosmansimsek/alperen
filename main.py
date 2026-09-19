import json
import os
import re
import time
from scraper import JobScraper
from analyzer import JobAnalyzer
from notifier import TelegramNotifier
from config import MIN_MATCH_SCORE

SEEN_JOBS_FILE = "seen_jobs.json"
SENT_MESSAGES_FILE = "sent_messages.txt"

def load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_jobs(seen_jobs: set):
    try:
        with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(seen_jobs), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ seen_jobs kaydedilirken hata: {e}")

def is_already_sent_to_telegram(title: str, company: str) -> bool:
    """sent_messages.txt içinde Ctrl+F mantığıyla başlık ve şirket arar."""
    if not os.path.exists(SENT_MESSAGES_FILE):
        return False
    
    clean_title = title.strip().lower()
    clean_company = company.strip().lower()

    try:
        with open(SENT_MESSAGES_FILE, "r", encoding="utf-8") as f:
            archive_content = f.read().lower()
            
            # Şirket biliniyorsa hem başlık hem şirket aynı anda var mı bakar
            if clean_company and clean_company not in ["seelink", "see job link", "unknown"]:
                if clean_title in archive_content and clean_company in archive_content:
                    return True
            else:
                # Şirket ismi yoksa doğrudan tam başlığı arar
                if len(clean_title) > 8 and clean_title in archive_content:
                    return True
    except Exception as e:
        print(f"⚠️ Arşiv okuma hatası: {e}")

    return False

def append_to_sent_archive(title: str, company: str, score: int, url: str):
    """Telegram'a atılan ilanı arşiv kütüğüne ekler."""
    log_entry = (
        f"----------------------------------------\n"
        f"Role: {title}\n"
        f"Company: {company}\n"
        f"Match Score: %{score}\n"
        f"URL: {url}\n"
        f"Date Added: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"----------------------------------------\n\n"
    )
    try:
        with open(SENT_MESSAGES_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"⚠️ Arşive yazma hatası: {e}")

def run_pipeline():
    print("==================================================")
    print("🚀 ÇİFT KATMANLI KONTROLLÜ İŞ ANALİZ MOTORU BAŞLATILDI")
    print("==================================================\n")

    notifier = TelegramNotifier()
    notifier.send_session_start_divider()

    scraper = JobScraper()
    analyzer = JobAnalyzer()

    seen_jobs = load_seen_jobs()
    jobs_by_site = scraper.fetch_jobs_site_by_site()

    total_matched = 0

    for site_name, jobs in jobs_by_site.items():
        print(f"\n==================================================")
        print(f"📂 SİTE BÖLÜMÜ BAŞLADI: {site_name} ({len(jobs)} İlan İncelemeye Alındı)")
        print(f"==================================================")

        if not jobs:
            print(f"⏩ {site_name} üzerinde uygun yeni iş bulunamadı, sonraki siteye geçiliyor...\n")
            continue

        for idx, job in enumerate(jobs, 1):
            job_id = job.get("id") or job.get("url")
            title = job.get("title", "Unknown Role")
            company = job.get("company", "Unknown Company")

            # 1. Katman Kontrolü: URL daha önce taranmış mı?
            if job_id in seen_jobs:
                print(f"   [{idx}/{len(jobs)}] URL zaten taranmış, geçiliyor: {title}")
                continue

            print(f"\n🧠 Analiz Ediliyor [{idx}/{len(jobs)}]: {title} @ {company}")
            
            eval_result = analyzer.evaluate_job(job)
            score = eval_result.get("match_score", 0)

            print(f"   📊 AI Uyum Puanı: %{score}")
            print(f"   💬 Neden: {eval_result.get('reason')}")

            # İlan barajı geçtiyse 2. Katman devreye girer:
            if score >= MIN_MATCH_SCORE:
                # 2. Katman Kontrolü: Ctrl+F Dosya Taraması
                if is_already_sent_to_telegram(title, company):
                    print(f"   🛑 TEKRAR İLAN ENGELLENDİ: Bu pozisyon ({title} @ {company}) daha önce Telegram'a atılmış!")
                else:
                    print(f"   🎯 BARAJI GEÇTİ (%{score} >= %{MIN_MATCH_SCORE})! Telegram'a yollanıyor...")
                    try:
                        notifier.send_job_notification(job, eval_result)
                        append_to_sent_archive(title, company, score, job.get("url", ""))
                        total_matched += 1
                    except Exception as e:
                        print(f"   ⚠️ Telegram bildirimi gönderilemedi: {e}")
                    time.sleep(1.0)

            # Taranan URL'yi hafızaya yaz
            seen_jobs.add(job_id)
            save_seen_jobs(seen_jobs)

        print(f"\n✅ {site_name} SİTESİNDEKİ TÜM İLANLARIN ANALİZİ TAMAMLANDI!")

    print("\n==================================================")
    print(f"🏁 TÜM SİTELER BİTTİ. Toplam {total_matched} adet YENİ nitelikli ilan Telegram'a iletildi.")
    print("==================================================")

if __name__ == "__main__":
    run_pipeline()
