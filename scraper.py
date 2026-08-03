# scraper.py
import re
import time
import random
import json
import os
import requests
from playwright.sync_api import sync_playwright

try:
    from config import MAX_JOBS_PER_SITE, REQUEST_DELAY
except ImportError:
    MAX_JOBS_PER_SITE = 100
    REQUEST_DELAY = (0.5, 1.5)

SEEN_JOBS_FILE = "seen_jobs.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

def _load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def _sleep():
    time.sleep(random.uniform(*REQUEST_DELAY))

def _clean_text(raw: str, limit: int = 3000) -> str:
    text = re.sub(r"\n{2,}", "\n", raw)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    return text[:limit]

def _handle_modals(page):
    """Pop-up, reklam ve cookie onaylarını kapatır."""
    modal_selectors = [
        "button[class*='close']", "[data-test='button-close']", 
        "div[class*='popup'] button", "button:has-text('✕')", "button:has-text('X')",
        "button:has-text('Akceptuj')", "button:has-text('Accept')", "button:has-text('Zgadzam się')",
        "#onetrust-accept-btn-handler", "[data-test='button-submitCookie']"
    ]
    for sel in modal_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=500):
                btn.click()
                time.sleep(0.2)
        except Exception:
            continue

def _extract_page_text(page) -> str:
    common_selectors = [
        "main", "article", "[role='main']",
        "#offer-description", ".job-description", ".job-details",
        ".description", "[data-test*='section']", "#jobDescriptionText"
    ]
    for sel in common_selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                txt = loc.inner_text(timeout=3000)
                if txt and len(txt.strip()) > 150:
                    return _clean_text(txt)
        except Exception:
            continue
    try:
        return _clean_text(page.inner_text("body"))
    except Exception:
        return ""


class JobScraper:
    def __init__(self):
        self.seen_jobs = _load_seen_jobs()
        # SİTEYE ÖZEL İLAN KART/DIV SELECTOR YAPISI
        self.target_sites = [
            # Pracuj.pl
            {"site": "Pracuj.pl - Analyst", "type": "generic", "url": "https://www.pracuj.pl/praca/analyst;kw/warszawa;wp?rd=30&et=1%2C17%2C4%2C18&wpl=true", "card_selector": "[data-test='default-offer'], [data-test='offer-title'], a[href*='/praca/']"},
            {"site": "Pracuj.pl - Compliance", "type": "generic", "url": "https://www.pracuj.pl/praca/compliance;kw/warszawa;wp?rd=30&et=1%2C17%2C4%2C18&wpl=true", "card_selector": "[data-test='default-offer'], [data-test='offer-title'], a[href*='/praca/']"},
            {"site": "Pracuj.pl - Risk", "type": "generic", "url": "https://www.pracuj.pl/praca/risk;kw/warszawa;wp?rd=30&et=1%2C17%2C4%2C18&wpl=true", "card_selector": "[data-test='default-offer'], [data-test='offer-title'], a[href*='/praca/']"},
            {"site": "Pracuj.pl - Operations", "type": "generic", "url": "https://www.pracuj.pl/praca/operations;kw/warszawa;wp?rd=30&et=1%2C17%2C4%2C18&wpl=true", "card_selector": "[data-test='default-offer'], [data-test='offer-title'], a[href*='/praca/']"},
            {"site": "Pracuj.pl - Turkish", "type": "generic", "url": "https://www.pracuj.pl/praca/turkish;kw/warszawa;wp?rd=30&et=1%2C17%2C4%2C18&wpl=true", "card_selector": "[data-test='default-offer'], [data-test='offer-title'], a[href*='/praca/']"},

            # RocketJobs
            {"site": "RocketJobs - Analyst EN", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?typ-umowy=umowa-o-prace&rodzaj-pracy=pelny-etat&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior&keyword=analyst&jezyk=en", "card_selector": "a[href*='/oferty-pracy/']"},
            {"site": "RocketJobs - Compliance EN", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?typ-umowy=umowa-o-prace&rodzaj-pracy=pelny-etat&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior&keyword=compliance&jezyk=en", "card_selector": "a[href*='/oferty-pracy/']"},
            {"site": "RocketJobs - Operations EN", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?typ-umowy=umowa-o-prace&rodzaj-pracy=pelny-etat&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior&keyword=operations&jezyk=en", "card_selector": "a[href*='/oferty-pracy/']"},
            {"site": "RocketJobs - Turkish EN", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?typ-umowy=umowa-o-prace&rodzaj-pracy=pelny-etat&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior&keyword=turkish&jezyk=en", "card_selector": "a[href*='/oferty-pracy/']"},

            # JustJoin.it
            {"site": "JustJoin.it - Junior", "type": "generic", "url": "https://justjoin.it/job-offers/warszawa?experience-level=junior&workplace=hybrid%2Cremote&working-hours=full-time&keyword=junior&orderBy=DESC&sortBy=newest", "card_selector": "a[href*='/job-offer/'], a[href*='/offers/']"},

            # XpatJobs
            {"site": "XpatJobs - Compliance", "type": "generic", "url": "https://poland.xpatjobs.com/search?ps=1&keyword=compliance&city=warsaw&areas=28", "card_selector": "a[href*='/job/'], a[href*='/vacancy/']"},
            {"site": "XpatJobs - Turkish", "type": "generic", "url": "https://poland.xpatjobs.com/search?ps=1&keyword=turkish&city=warsaw&areas=28", "card_selector": "a[href*='/job/'], a[href*='/vacancy/']"},

            # CareersInPoland
            {"site": "CareersInPoland", "type": "generic", "url": "https://www.careersinpoland.com/jobs/language/english+turkish/city/remote+warszawa", "card_selector": "a[href*='/job/'], a[href*='/jobs/']"},

            # JobLeads
            {"site": "JobLeads - Compliance", "type": "generic", "url": "https://www.jobleads.com/pl/jobs/l/Warszawa/q/compliance?filter_by_daysReleased=14&filter_by_remote=hybrid,remote&minSalary=120000", "card_selector": "a[href*='/job/']"},
            {"site": "JobLeads - Turkish", "type": "generic", "url": "https://www.jobleads.com/pl/jobs/l/Warszawa/q/turkish?filter_by_daysReleased=14&filter_by_remote=hybrid,remote&minSalary=120000", "card_selector": "a[href*='/job/']"},

            # Talent.com
            {"site": "Talent.com - Compliance", "type": "generic", "url": "https://pl.talent.com/en/jobs?k=compliance&l=Warsaw%2C+Mazovia&radius=5", "card_selector": "a[href*='/view']"},
            {"site": "Talent.com - Turkish", "type": "generic", "url": "https://pl.talent.com/en/jobs?k=turkish&l=Warsaw%2C+Mazovia&radius=5", "card_selector": "a[href*='/view']"},

            # Indeed
            {"site": "Indeed - Compliance", "type": "generic", "url": "https://pl.indeed.com/jobs?q=compliance&l=Warszawa%2C%20mazowieckie&radius=10&from=searchOnDesktopSerp", "card_selector": "a[id^='job_'], a[class*='jcs-JobTitle']"},
            {"site": "Indeed - Turkish", "type": "generic", "url": "https://pl.indeed.com/jobs?q=turkish&l=Warszawa%2C%20mazowieckie&radius=10&from=searchOnDesktopSerp", "card_selector": "a[id^='job_'], a[class*='jcs-JobTitle']"},

            # LinkedIn Guest (Çoklu Sayfa)
            {"site": "LinkedIn - Analyst", "type": "linkedin_guest", "keywords": "Analyst", "f_E": "1,2", "f_WT": "2,3,1"},
            {"site": "LinkedIn - Compliance", "type": "linkedin_guest", "keywords": "Compliance", "f_E": "1,2", "f_WT": "2,3,1"},
            {"site": "LinkedIn - Risk", "type": "linkedin_guest", "keywords": "risk", "f_E": "1,2", "f_WT": "2,3,1"},
            {"site": "LinkedIn - Operations", "type": "linkedin_guest", "keywords": "Operations", "f_E": "1,2", "f_WT": "2,3,1"},
            {"site": "LinkedIn - Turkish", "type": "linkedin_guest", "keywords": "turkish", "f_E": "1,2", "f_WT": "2,3,1"},
        ]

    def _scrape_generic(self, context, target: dict) -> list:
        site_name = target["site"]
        jobs = []
        page = context.new_page()
        try:
            try:
                page.goto(target["url"], timeout=15000, wait_until="domcontentloaded")
            except Exception:
                pass

            time.sleep(1.5)
            _handle_modals(page)

            # DERİN AŞAĞI KAYDIRMA (Scroll & Dinamik Yükleme)
            for _ in range(5):
                page.mouse.wheel(0, 2500)
                time.sleep(0.7)

            base = "/".join(target["url"].split("/")[:3])
            candidates = []
            local_seen = set()

            # Inspect Elemanı Mantığıyla İlan Kartlarını Çek
            card_sel = target.get("card_selector", "a")
            elements = page.locator(card_sel).all()

            for el in elements:
                try:
                    href = el.get_attribute("href")
                    title = el.inner_text().strip()
                    if not href:
                        continue

                    full_url = base + href if href.startswith("/") else href

                    if full_url in self.seen_jobs or full_url in local_seen or full_url == target["url"]:
                        continue

                    local_seen.add(full_url)
                    clean_title = title if len(title) > 3 else "Job Opportunity"
                    candidates.append({"url": full_url, "title": clean_title})
                except Exception:
                    continue

            candidates = candidates[:MAX_JOBS_PER_SITE]
            print(f"   --> {site_name}: {len(candidates)} adet YENİ ilan kartı yakalandı.")

            # Her ilanı sanki yan sekmede açıyormuş gibi okuma
            for cand in candidates:
                detail_page = context.new_page()
                try:
                    detail_page.goto(cand["url"], timeout=15000, wait_until="domcontentloaded")
                    time.sleep(1)
                    _handle_modals(detail_page)

                    full_text = _extract_page_text(detail_page)
                    if len(full_text) < 100:
                        continue

                    jobs.append({
                        "id": cand["url"],
                        "source_site": site_name,
                        "title": cand["title"].replace("\n", " ")[:150],
                        "company": "See Job Link",
                        "city": "Warsaw / Remote",
                        "url": cand["url"],
                        "description": full_text,
                    })
                except Exception as e:
                    print(f"      ⚠️ Detay okunamadı: {e}")
                finally:
                    detail_page.close()
                    _sleep()

        except Exception as e:
            print(f"   ⚠️ {site_name} taranırken hata: {e}")
        finally:
            page.close()

        return jobs

    def _scrape_linkedin_guest(self, target: dict) -> list:
        site_name = target["site"]
        jobs = []
        headers = {"User-Agent": USER_AGENT}

        # Sayfa Sayfa (0, 25, 50, 75 offset) Gezerek İlan Toplama
        for start_offset in range(0, 100, 25):
            search_url = (
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                f"?keywords={target['keywords']}&location=Warsaw%2C%20Poland"
                f"&f_E={target['f_E']}&f_WT={target['f_WT']}&start={start_offset}"
            )
            try:
                res = requests.get(search_url, headers=headers, timeout=20)
                if res.status_code != 200:
                    break

                job_urns = re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)"', res.text)
                titles = re.findall(r'base-search-card__title">\s*([^<]+)', res.text)
                companies = re.findall(r'base-search-card__subtitle">.*?>\s*([^<]+)', res.text, re.S)

                if not job_urns:
                    break

                for i in range(len(job_urns)):
                    job_id = job_urns[i]
                    job_url = f"https://www.linkedin.com/jobs/view/{job_id}"

                    if job_url in self.seen_jobs:
                        continue

                    title = titles[i].strip() if i < len(titles) else "Unknown Title"
                    company = companies[i].strip() if i < len(companies) else "Unknown"

                    desc_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
                    description = f"Title: {title}. Company: {company}."
                    try:
                        d_res = requests.get(desc_url, headers=headers, timeout=15)
                        if d_res.status_code == 200:
                            match = re.search(
                                r'show-more-less-html__markup[^>]*>(.*?)</div>', d_res.text, re.S
                            )
                            if match:
                                raw = re.sub(r"<[^>]+>", " ", match.group(1))
                                description = _clean_text(raw)
                    except Exception:
                        pass

                    jobs.append({
                        "id": job_url,
                        "source_site": site_name,
                        "title": title,
                        "company": company,
                        "city": "Warsaw / Remote",
                        "url": job_url,
                        "description": description,
                    })
                    _sleep()

            except Exception as e:
                print(f"   ⚠️ {site_name} (guest) sayfa offset {start_offset} hatası: {e}")
                break

        print(f"   --> {site_name}: Toplam {len(jobs)} adet YENİ ilan çekildi.")
        return jobs

    def fetch_jobs_site_by_site(self) -> dict:
        site_jobs = {}
        print("🌐 GELİŞMİŞ DOM & INSPECTION TARAMA MOTORU BAŞLATILDI...")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                locale="pl-PL",
                viewport={"width": 1280, "height": 800}
            )

            for target in self.target_sites:
                site_name = target["site"]
                print(f"\n🔄 Taranan: {site_name}...")

                if target["type"] == "linkedin_guest":
                    site_jobs[site_name] = self._scrape_linkedin_guest(target)
                else:
                    site_jobs[site_name] = self._scrape_generic(context, target)

                print(f"   ✅ {site_name}: {len(site_jobs[site_name])} adet incelenecek yeni ilan çekildi.")

            browser.close()

        return site_jobs