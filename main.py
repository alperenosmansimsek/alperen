# main.py
import json
import os
import time
from scraper import JobScraper
from analyzer import JobAnalyzer
from notifier import TelegramNotifier
from config import MIN_MATCH_SCORE

SEEN_JOBS_FILE = "seen_jobs.json"

def load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_seen_jobs(seen_jobs: set):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen_jobs), f, indent=2)

def run_pipeline():
    print("==================================================")
    print("🤖 GROQ AI PUANLAMALI İŞ ANALİZ MOTORU BAŞLATILDI")
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

            if job_id in seen_jobs:
                print(f"   [{idx}/{len(jobs)}] Zaten incelendi, geçiliyor: {job['title']}")
                continue

            print(f"\n🧠 Analiz Ediliyor [{idx}/{len(jobs)}]: {job['title']} @ {job['company']}")
            
            eval_result = analyzer.evaluate_job(job)
            score = eval_result.get("match_score", 0)

            print(f"   📊 AI Uyum Puanı: %{score}")
            print(f"   💬 Neden: {eval_result['reason']}")

            if score >= MIN_MATCH_SCORE:
                print(f"   🎯 BARAJI GEÇTİ (%{score} >= %{MIN_MATCH_SCORE})! Telegram'a yollanıyor...")
                notifier.send_job_notification(job, eval_result)
                total_matched += 1
                time.sleep(1)

            seen_jobs.add(job_id)
            save_seen_jobs(seen_jobs)
            time.sleep(0.3)

        print(f"\n✅ {site_name} SİTESİNDEKİ TÜM İLANLARIN ANALİZİ TAMAMLANDI!")

    print("\n==================================================")
    print(f"🏁 TÜM SİTELER BİTTİ. Toplam {total_matched} adet nitelikli ilan Telegram'a iletildi.")
    print("==================================================")

if __name__ == "__main__":
    run_pipeline()