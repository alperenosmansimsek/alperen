import json
import os
import re
import time
from urllib.parse import urlparse, urlunparse

from scraper import JobScraper
from analyzer import JobAnalyzer
from notifier import TelegramNotifier
from config import MIN_MATCH_SCORE

SEEN_JOBS_FILE = "seen_jobs.json"
SENT_TITLES_FILE = "sent_titles.json"
SENT_MESSAGES_FILE = "sent_messages.txt"


def clean_job_title(title: str) -> str:
    """
    Başlıktaki tüm gürültüleri (parantezler, lokasyon, seviye ekleri) temizleyip
    saf kök unvanı çıkarır.
    Örn: 'Data Analyst ( Commercial Operations) - Warsaw (Hybrid)' -> 'dataanalystcommercialoperations'
    """
    t = title.lower()
    t = re.sub(r'\(.*?\)|\[.*?\]', '', t)
    t = re.sub(r'\b(hybrid|remote|warsaw|warszawa|poland|polska|k/m|m/f/d|f/m/x|m/f/x|full-time|part-time|warszawa|gliwice|lodz|wroclaw)\b', '', t)
    t = re.sub(r'[^a-z0-9]', '', t)
    return t


def load_sent_titles() -> set:
    if os.path.exists(SENT_TITLES_FILE):
        try:
            with open(SENT_TITLES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()
    return set()


def save_sent_titles(sent_titles: set):
    try:
        with open(SENT_TITLES_FILE, "w", encoding="utf-8") as f:
            json.dump(list(sent_titles), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ sent_titles kaydedilemedi: {e}")


def load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()
    return set()


def save_seen_jobs(seen_jobs: set):
    try:
        cleaned = list(seen_jobs)
        if len(cleaned) > 5000:
            cleaned = cleaned[-4000:]
        with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ seen_jobs kaydedilemedi: {e}")


def append_to_sent_archive(job: dict, score: int, signature: str):
    log_entry = (
        f"----------------------------------------\n"
        f"SIGNATURE: {signature}\n"
        f"Role: {job.get('title', '')}\n"
        f"Company: {job.get('company', '')}\n"
        f"Match Score: %{score}\n"
        f"URL: {job.get('url', '')}\n"
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
    print("🚀 SIFIR-TEKRAR GARANTİLİ İŞ MOTORU (v2.1) BAŞLATILDI")
    print("==================================================\n")

    notifier = TelegramNotifier()
    notifier.send_session_start_divider()

    scraper = JobScraper()
    analyzer = JobAnalyzer()

    seen_jobs = load_seen_jobs()
    sent_titles = load_sent_titles()

    jobs_by_site = scraper.fetch_jobs_site_by_site()
    total_matched = 0

    for site_name, jobs in jobs_by_site.items():
        print(f"\n==================================================")
        print(f"📂 BÖLÜM: {site_name} ({len(jobs)} İlan Taramada)")
        print(f"==================================================")

        if not jobs:
            continue

        site_new_seen = 0

        for idx, job in enumerate(jobs, 1):
            raw_url = job.get("url") or job.get("id", "")
            title = job.get("title", "Unknown Role").strip()
            company = job.get("company", "Unknown Company").strip()

            clean_sig = clean_job_title(title)

            # 1. KONTROL: URL daha önce taranmış mı?
            if raw_url in seen_jobs:
                continue

            # 2. KESİN KONTROL: Bu başlık daha önce Telegram'a yollandı mı?
            if len(clean_sig) > 6 and clean_sig in sent_titles:
                print(f"   🛑 [MÜKERRER BLOKE]: '{title}' daha önce Telegram'a atılmış!")
                seen_jobs.add(raw_url)
                continue

            print(f"\n🧠 Analiz Ediliyor [{idx}/{len(jobs)}]: {title} @ {company}")

            eval_result = analyzer.evaluate_job(job)
            score = eval_result.get("match_score", 0)

            print(f"   📊 AI Uyum Puanı: %{score}")
            print(f"   💬 Neden: {eval_result.get('reason')}")

            # Barajı geçtiyse
            if score >= MIN_MATCH_SCORE:
                # İkinci güvenlik: Başlık kütüğünde tekrar teyit
                if clean_sig in sent_titles:
                    print(f"   🛑 [MÜKERRER BLOKE]: Son kontrolde yakalandı: {title}")
                else:
                    print(f"   🎯 BARAJI GEÇTİ (%{score} >= %{MIN_MATCH_SCORE})! Telegram'a yollanıyor...")
                    try:
                        notifier.send_job_notification(job, eval_result)
                        sent_titles.add(clean_sig)
                        save_sent_titles(sent_titles)
                        append_to_sent_archive(job, score, clean_sig)
                        total_matched += 1
                        time.sleep(1.0)
                    except Exception as e:
                        print(f"   ⚠️ Telegram bildirimi gönderilemedi: {e}")

            seen_jobs.add(raw_url)
            site_new_seen += 1

        if site_new_seen > 0:
            save_seen_jobs(seen_jobs)

    save_seen_jobs(seen_jobs)
    save_sent_titles(sent_titles)

    print("\n==================================================")
    print(f"🏁 SEANS BİTTİ. Toplam {total_matched} adet YENİ nitelikli ilan iletildi.")
    print("==================================================")


if __name__ == "__main__":
    run_pipeline()
