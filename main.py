import json
import os
import re
import time
import hashlib
from urllib.parse import urlparse, urlunparse

from scraper import JobScraper
from analyzer import JobAnalyzer
from notifier import TelegramNotifier
from config import MIN_MATCH_SCORE

SEEN_JOBS_FILE = "seen_jobs.json"
SENT_MESSAGES_FILE = "sent_messages.txt"


def sanitize_url(raw_url: str) -> str:
    """İzleme ve session parametrelerini URL'den temizler."""
    if not raw_url:
        return ""
    try:
        parsed = urlparse(raw_url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    except Exception:
        return raw_url.split("?")[0]


def generate_bulletproof_id(job: dict) -> str:
    """
    İlanın linki veya başlık formatı değişse bile aynı iş için
    HER ZAMAN aynı benzersiz hash ID'yi üretir.
    """
    url = job.get("url") or job.get("id", "")
    title = job.get("title", "")
    company = job.get("company", "")

    # 1. LinkedIn ise değişmeyen sayısal Job ID'yi al
    linkedin_match = re.search(r'/jobs/view/(\d+)', url)
    if linkedin_match:
        return f"li_{linkedin_match.group(1)}"

    # 2. Başlıktaki parantez içi ve lokasyon gürültülerini temizle
    clean_title = title.lower()
    clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', clean_title)
    clean_title = re.sub(r'\b(hybrid|remote|warsaw|warszawa|poland|polska|k/m|m/f/d|full-time)\b', '', clean_title)
    clean_title = re.sub(r'[^a-z0-9]', '', clean_title)

    # 3. Şirket uzantılarını temizle
    clean_comp = company.lower()
    clean_comp = re.sub(r'\b(sp\.?\s*z\s*o\.?\s*o\.?|s\.?a\.?|poland|polska|emea|group|inc\.?|llc)\b', '', clean_comp)
    clean_comp = re.sub(r'[^a-z0-9]', '', clean_comp)

    # Şirket adı jenerik kaldıysa temiz URL yolunu baz al
    if not clean_comp or clean_comp in ["seelink", "seejoblink", "unknown"]:
        parsed = urlparse(url)
        clean_path = re.sub(r'[^a-z0-9]', '', parsed.path)
        raw_identity = f"{clean_title}_{clean_path}"
    else:
        raw_identity = f"{clean_comp}_{clean_title}"

    return hashlib.md5(raw_identity.encode('utf-8')).hexdigest()[:12]


def load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception as e:
            print(f"⚠️ seen_jobs okuma hatası: {e}")
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
        print(f"⚠️ seen_jobs kaydedilirken hata: {e}")


def is_already_in_sent_archive(job: dict) -> bool:
    """sent_messages.txt dosyasında parmak izi veya rol+şirket bazlı kontrol yapar."""
    if not os.path.exists(SENT_MESSAGES_FILE):
        return False

    title = job.get("title", "")
    company = job.get("company", "")
    job_uid = generate_bulletproof_id(job)

    clean_t = re.sub(r'[^a-z0-9]', '', title.lower())
    clean_c = re.sub(r'[^a-z0-9]', '', company.lower())

    try:
        with open(SENT_MESSAGES_FILE, "r", encoding="utf-8") as f:
            archive = f.read()

        # Doğrudan Hash ID kontrolü
        if f"ID: {job_uid}" in archive:
            return True

        # Blok bazlı Role ve Company satır kontrolü
        blocks = archive.split("----------------------------------------")
        for blk in blocks:
            role_match = re.search(r'Role:\s*(.+)', blk, re.IGNORECASE)
            comp_match = re.search(r'Company:\s*(.+)', blk, re.IGNORECASE)

            if role_match:
                blk_role = re.sub(r'[^a-z0-9]', '', role_match.group(1).lower())
                blk_comp = re.sub(r'[^a-z0-9]', '', comp_match.group(1).lower()) if comp_match else ""

                if clean_c and clean_c not in ["seelink", "seejoblink", "unknown"]:
                    if blk_comp and blk_comp == clean_c and blk_role == clean_t:
                        return True
                elif blk_role and blk_role == clean_t:
                    return True
    except Exception as e:
        print(f"⚠️ Arşiv okuma hatası: {e}")

    return False


def append_to_sent_archive(job: dict, score: int, job_uid: str):
    """Gönderilen ilanı sent_messages.txt kütüğüne işler."""
    log_entry = (
        f"----------------------------------------\n"
        f"ID: {job_uid}\n"
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
    print("🚀 GÜVENLİ ÇİFT KATMANLI İŞ MOTORU (v2.0) BAŞLATILDI")
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
        print(f"📂 SİTE BÖLÜMÜ: {site_name} ({len(jobs)} İlan Taramada)")
        print(f"==================================================")

        if not jobs:
            print(f"⏩ {site_name} üzerinde yeni ilan yok, geçiliyor...\n")
            continue

        site_new_seen = 0

        for idx, job in enumerate(jobs, 1):
            raw_url = job.get("url") or job.get("id", "")
            clean_url = sanitize_url(raw_url)
            job_uid = generate_bulletproof_id(job)
            title = job.get("title", "Unknown Role").strip()
            company = job.get("company", "Unknown Company").strip()

            # 1. Katman: URL veya Hash ID daha önce taranmış mı?
            if clean_url in seen_jobs or raw_url in seen_jobs or job_uid in seen_jobs:
                print(f"   [{idx}/{len(jobs)}] Zaten taranmış, atlanıyor: {title}")
                continue

            print(f"\n🧠 Analiz Ediliyor [{idx}/{len(jobs)}]: {title} @ {company}")

            eval_result = analyzer.evaluate_job(job)
            score = eval_result.get("match_score", 0)

            print(f"   📊 AI Uyum Puanı: %{score}")
            print(f"   💬 Neden: {eval_result.get('reason')}")

            # 2. Katman: Barajı geçtiyse geçmiş mesaj arşivini tara
            if score >= MIN_MATCH_SCORE:
                if is_already_in_sent_archive(job):
                    print(f"   🛑 MÜKERRER ENGELİ: Bu pozisyon ({title} @ {company}) daha önce Telegram'a atılmış!")
                else:
                    print(f"   🎯 BARAJI GEÇTİ (%{score} >= %{MIN_MATCH_SCORE})! Telegram'a yollanıyor...")
                    try:
                        notifier.send_job_notification(job, eval_result)
                        append_to_sent_archive(job, score, job_uid)
                        total_matched += 1
                        time.sleep(1.0)
                    except Exception as e:
                        print(f"   ⚠️ Telegram bildirimi gönderilemedi: {e}")

            # Hafızaya ekle
            seen_jobs.add(clean_url)
            seen_jobs.add(job_uid)
            if raw_url:
                seen_jobs.add(raw_url)
            site_new_seen += 1

        # Her site bittiğinde diske güvenle kaydet
        if site_new_seen > 0:
            save_seen_jobs(seen_jobs)

        print(f"\n✅ {site_name} BÖLÜMÜ TAMAMLANDI!")

    # Seans bitimi son kayıt
    save_seen_jobs(seen_jobs)

    print("\n==================================================")
    print(f"🏁 TÜM SİTELER BİTTİ. Toplam {total_matched} adet YENİ nitelikli ilan Telegram'a iletildi.")
    print("==================================================")


if __name__ == "__main__":
    run_pipeline()
