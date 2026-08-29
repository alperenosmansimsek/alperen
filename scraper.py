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
        self.target_sites = [
            # 📌 Pracuj.pl (Son 7 Gün & Junior/Mid/Staż Filtresi)
            {"site": "Pracuj.pl - Analyst", "type": "pracuj", "url": "https://www.pracuj.pl/praca/analyst;kw/warszawa;wp/ostatnich%207%20dni;p,7?rd=10&et=1%2C17%2C4%2C18%2C3%2C19%2C5%2C20%2C6%2C21%2C2&wpl=true&tm=7", "card_selector": "div[data-test='default-offer'] a[data-test='link-offer'], a[href*='oferta']"},
            {"site": "Pracuj.pl - Compliance", "type": "pracuj", "url": "https://www.pracuj.pl/praca/compliance;kw/warszawa;wp/ostatnich%207%20dni;p,7?rd=10&et=1%2C17%2C4%2C18%2C3%2C19%2C5%2C20%2C6&wpl=true&tm=7", "card_selector": "div[data-test='default-offer'] a[data-test='link-offer'], a[href*='oferta']"},
            {"site": "Pracuj.pl - Risk", "type": "pracuj", "url": "https://www.pracuj.pl/praca/risk;kw/warszawa;wp/ostatnich%207%20dni;p,7?rd=10&et=1%2C17%2C4%2C18%2C3%2C19%2C5%2C20%2C6%2C21&wpl=true&tm=7", "card_selector": "div[data-test='default-offer'] a[data-test='link-offer'], a[href*='oferta']"},
            {"site": "Pracuj.pl - Operations", "type": "pracuj", "url": "https://www.pracuj.pl/praca/operations;kw/warszawa;wp/ostatnich%207%20dni;p,7?rd=10&et=1%2C17%2C4%2C18%2C3%2C19%2C5%2C20%2C6&wpl=true&tm=7", "card_selector": "div[data-test='default-offer'] a[data-test='link-offer'], a[href*='oferta']"},
            {"site": "Pracuj.pl - Turkish", "type": "pracuj", "url": "https://www.pracuj.pl/praca/turkish;kw/warszawa;wp/ostatnich%207%20dni;p,7?rd=10&tm=7", "card_selector": "div[data-test='default-offer'] a[data-test='link-offer'], a[href*='oferta']"},
            
            # 📌 RocketJobs (Site yapısı gereği tarih filtresi varsayılan olarak taze ilanları üstte verir)
            {"site": "RocketJobs - Analyst", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?radius=10&typ-umowy=umowa-o-prace&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior,starszy-specjalista-senior,kierownik-manager&keyword=analyst&data-publikacji=14&jezyk=en", "card_selector": "a[href^='/oferta/'], a[href*='/oferty-pracy/']"},
            {"site": "RocketJobs - Compliance EN", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?radius=10&typ-umowy=umowa-o-prace&rodzaj-pracy=pelny-etat&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior,starszy-specjalista-senior,dyrektor-c-level,kierownik-manager&keyword=compliance&data-publikacji=14&jezyk=en#more-filters", "card_selector": "a[href^='/oferta/'], a[href*='/oferty-pracy/']"},
            {"site": "RocketJobs - Risk EN", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?radius=10&typ-umowy=umowa-o-prace&rodzaj-pracy=pelny-etat&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior,kierownik-manager,starszy-specjalista-senior,dyrektor-c-level&keyword=risk&data-publikacji=14&jezyk=en", "card_selector": "a[href^='/oferta/'], a[href*='/oferty-pracy/']"},
            {"site": "RocketJobs - Operations EN", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?radius=10&typ-umowy=umowa-o-prace&rodzaj-pracy=pelny-etat&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior,kierownik-manager,starszy-specjalista-senior,dyrektor-c-level&keyword=operations&data-publikacji=14&jezyk=en#more-filters", "card_selector": "a[href^='/oferta/'], a[href*='/oferty-pracy/']"},
            {"site": "RocketJobs - Turkish EN", "type": "generic", "url": "https://rocketjobs.pl/oferty-pracy/warszawa?radius=10&typ-umowy=umowa-o-prace&rodzaj-pracy=pelny-etat&doswiadczenie=specjalista-mid,mlodszy-specjalista-junior,starszy-specjalista-senior,kierownik-manager,dyrektor-c-level&keyword=turkish&jezyk=en#more-filters", "card_selector": "a[href^='/oferta/'], a[href*='/oferty-pracy/']"},
            
            # 📌 JustJoin.it
            {"site": "JustJoin.it - Junior/Mid", "type": "generic", "url": "https://justjoin.it/job-offers/warszawa?radius=10&employment-types=permanent&working-times=full-time&experience-levels=junior,mid,team-leader-manager,senior,c-level&published-date=7&languages=en&sortBy=newest", "card_selector": "a[href*='/job-offer/'], a[href*='/offers/']"},

            # 📌 JobLeads (Zaten 7 Gün ayarlı: filter_by_daysReleased=7)
            {"site": "JobLeads - Compliance", "type": "generic", "url": "https://www.jobleads.com/pl/jobs/l/Warszawa/q/compliance?filter_by_daysReleased=7&minSalary=100000", "card_selector": "a[href*='/job/']"},
            {"site": "JobLeads - Turkish", "type": "generic", "url": "https://www.jobleads.com/pl/jobs/l/Warszawa/q/turkish?filter_by_daysReleased=7&minSalary=100000", "card_selector": "a[href*='/job/']"},
            {"site": "JobLeads - Tax", "type": "generic", "url": "https://www.jobleads.com/pl/jobs/l/Warszawa/q/tax?filter_by_daysReleased=7&minSalary=100000", "card_selector": "a[href*='/job/']"},
            {"site": "JobLeads - Accountant", "type": "generic", "url": "https://www.jobleads.com/pl/jobs/l/Warszawa/q/accountant?filter_by_daysReleased=7&minSalary=100000", "card_selector": "a[href*='/job/']"},

            # 📌 Indeed (Son 7 Gün: &fromage=7)
            {"site": "Indeed - Compliance", "type": "generic", "url": "https://pl.indeed.com/jobs?q=compliance&l=Warszawa&fromage=7&lang=en&radius=10&sc=0kf%3Aattr%285QWDV%7CCF3CP%252COR%29%3B&from=searchOnDesktopSerp&vjk=0444a2df8dccf399", "card_selector": "a[id^='job_'], a[class*='jcs-JobTitle']"},
            {"site": "Indeed - Turkish", "type": "generic", "url": "https://pl.indeed.com/jobs?q=turkish&l=Warszawa&fromage=7", "card_selector": "a[id^='job_'], a[class*='jcs-JobTitle']"},
            {"site": "Indeed -  - ", "type": "generic", "url": "https://pl.indeed.com/jobs?q=&l=Warszawa&sort=date&fromage=7&lang=en&radius=25&sc=0kf%3Aattr%285QWDV%7CCF3CP%252COR%29%3B&from=searchOnDesktopSerp", "card_selector": "a[id^='job_'], a[class*='jcs-JobTitle']"},
            
            # 📌 LinkedIn Guest (Son 7 Gün: f_TPR=r604800)
            {"site": "LinkedIn - Analyst", "type": "linkedin_guest", "keywords": "Analyst", "f_E": "1,2,3", "f_WT": "2,3,1", "f_TPR": "r604800"},
            {"site": "LinkedIn - Compliance", "type": "linkedin_guest", "keywords": "Compliance", "f_E": "1,2,3", "f_WT": "2,3,1", "f_TPR": "r604800"},
            {"site": "LinkedIn - Risk", "type": "linkedin_guest", "keywords": "Risk", "f_E": "1,2,3", "f_WT": "2,3,1", "f_TPR": "r604800"},
            {"site": "LinkedIn - Operations", "type": "linkedin_guest", "keywords": "Operations", "f_E": "1,2,3", "f_WT": "2,3,1", "f_TPR": "r604800"},
            {"site": "LinkedIn - Turkish", "type": "linkedin_guest", "keywords": "Turkish", "f_E": "1,2,3", "f_WT": "2,3,1", "f_TPR": "r604800"},
        ]

    def _scrape_generic(self, context, target: dict) -> list:
        site_name = target["site"]
        base_url = target["url"]
        jobs = []
        local_seen = set()
        candidates = []

        page = context.new_page()
        try:
            page_idx = 1
            max_pages = 5
            empty_pages_count = 0

            while page_idx <= max_pages:
                page_url = base_url
                if "pracuj.pl" in base_url:
                    sep = "&" if "?" in base_url else "?"
                    page_url = f"{base_url}{sep}pn={page_idx}"

                try:
                    page.goto(page_url, timeout=20000, wait_until="domcontentloaded")
                except Exception:
                    pass

                time.sleep(1.5)
                _handle_modals(page)

                for _ in range(4):
                    page.mouse.wheel(0, 1500)
                    time.sleep(0.3)

                card_sel = target.get("card_selector", "a")
                elements = page.locator(card_sel).all()
                base_domain = "/".join(page_url.split("/")[:3])

                page_new_found = 0
                for el in elements:
                    try:
                        href = el.get_attribute("href")
                        title = el.inner_text().strip()
                        if not href:
                            continue

                        full_url = base_domain + href if href.startswith("/") else href
                        clean_url = full_url.split("?")[0]

                        # Çöp kategori linklerini ele
                        if any(c in clean_url for c in ["/kategorie/", "/sprzedaz", "/marketing", "/budownictwo", "/edukacja"]):
                            continue

                        if (clean_url in self.seen_jobs or 
                            clean_url in local_seen or 
                            clean_url == page_url or 
                            len(clean_url) < 18):
                            continue

                        local_seen.add(clean_url)
                        clean_title = title.split("\n")[0].strip() if title else "Job Opportunity"
                        candidates.append({"url": full_url, "title": clean_title})
                        page_new_found += 1
                    except Exception:
                        continue

                if page_new_found == 0:
                    empty_pages_count += 1
                    if empty_pages_count >= 2:
                        break
                else:
                    empty_pages_count = 0

                page_idx += 1

            candidates = candidates[:MAX_JOBS_PER_SITE]
            print(f"   --> {site_name}: {len(candidates)} adet YENİ ilan kartı yakalandı.")

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
        tpr = target.get("f_TPR", "r604800")

        for start_offset in range(0, 100, 25):
            search_url = (
                "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                f"?keywords={target['keywords']}&location=Warsaw%2C%20Poland"
                f"&f_E={target['f_E']}&f_WT={target['f_WT']}&f_TPR={tpr}&start={start_offset}"
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
