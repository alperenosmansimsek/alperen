import json
import os
import re
import time
from scraper import JobScraper
from analyzer import JobAnalyzer
from notifier import TelegramNotifier
from config import MIN_MATCH_SCORE

SEEN_JOBS_FILE = "seen_jobs.json"

def normalize_text(text: str) -> str:
    """Metindeki özel karakterleri temizler ve küçük harfe çevirir."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def generate_job_fingerprint(job: dict) -> str:
    """Firma adı ve pozisyon başlığını birleştirip tekil kimlik üretir."""
    comp = normalize_text(job.get("company", ""))
    title = normalize_text(job.get("title", ""))
    
    # Firma ismi link içeriğindeyse veya boşsa URL'yi baz al
    if not comp or comp in ["seelink", "seejoblink", "unknown"]:
        return normalize_text(job.get("url", ""))
    return f"fp_{comp}_{title}"

def load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data)
        except Exception:
            return set()
    return set()

def save_seen_jobs(seen_jobs: set):
    try:
        # Liste boyutu 5000'i geçerse en eski kayıtları kırpıp korur
        cleaned_list = list(seen_jobs)
        if len(cleaned_list) > 5000:
            cleaned_list = cleaned_list[-4000:]

        with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned_list, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ seen_jobs kaydedilirken hata: {e}")

def run_pipeline():
    print("==================================================")
    print("🚀 DETERMINISTIC AI PUANLAMALI İŞ ANALİZ MOTORU BAŞLATILDI")
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
            job_fp = generate_job_fingerprint(job)

            # Hem link hem de Firma + Pozisyon kontrol edilir
            if job_id in seen_jobs or job_fp in seen_jobs:
                print(f"   [{idx}/{len(jobs)}] Zaten gönderilmiş/incelenmiş, geçiliyor: {job.get('title', 'Unknown')} @ {job.get('company', 'Unknown')}")
                continue

            print(f"\n🧠 Analiz Ediliyor [{idx}/{len(jobs)}]: {job.get('title')} @ {job.get('company')}")
            
            eval_result = analyzer.evaluate_job(job)
            score = eval_result.get("match_score", 0)

            print(f"   📊 AI Uyum Puanı: %{score}")
            print(f"   💬 Neden: {eval_result.get('reason')}")

            if score >= MIN_MATCH_SCORE:
                print(f"   🎯 BARAJI GEÇTİ (%{score} >= %{MIN_MATCH_SCORE})! Telegram'a yollanıyor...")
                try:
                    notifier.send_job_notification(job, eval_result)
                    total_matched += 1
                except Exception as e:
                    print(f"   ⚠️ Telegram bildirimi gönderilemedi: {e}")
                time.sleep(1.0)

            # Hem URL'yi hem de parmak izini kaydet
            seen_jobs.add(job_id)
            seen_jobs.add(job_fp)
            save_seen_jobs(seen_jobs)

        print(f"\n✅ {site_name} SİTESİNDEKİ TÜM İLANLARIN ANALİZİ TAMAMLANDI!")

    print("\n==================================================")
    print(f"🏁 TÜM SİTELER BİTTİ. Toplam {total_matched} adet nitelikli ilan Telegram'a iletildi.")
    print("==================================================")

if __name__ == "__main__":
    run_pipeline()
