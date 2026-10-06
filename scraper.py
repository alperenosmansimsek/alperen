import json
import os
import random
import re
import time
import requests
from playwright.sync_api import sync_playwright

try:
    from config import MAX_JOBS_PER_SITE, REQUEST_DELAY
except ImportError:
    MAX_JOBS_PER_SITE = 35
    REQUEST_DELAY = (0.5, 1.2)

SEEN_JOBS_FILE = "seen_jobs.json"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

def _load_seen_jobs() -> set:
    if os.path.exists(SEEN_JOBS_FILE):
        try:
            with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()
    return set()

def _sleep():
    time.sleep(random.uniform(*REQUEST_DELAY))

def _clean_text(raw: str, limit: int = 3500) -> str:
    text = re.sub(r"\n{2,}", "\n", raw)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    return text[:limit]

def _handle_modals(page):
    modal_selectors = [
        "button[class*='close']", "[data-test='button-close']", 
        "div[class*='popup'] button", "button:has-text('✕')", "button:has-text('X')",
        "button:has-text('Akceptuj')", "button:has-text('Accept')", "button:has-text('Zgadzam się')",
        "#onetrust-accept-btn-handler", "[data-test='button-submitCookie']",
        "button[id*='cookie']", "button[class*='cookie']"
    ]
    for sel in modal_selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=250):
                btn.click()
                time.sleep(0.15)
        except Exception:
            continue

def _scroll_page(page, scrolls: int = 4):
    for _ in range(scrolls):
        page.mouse.wheel(0, 1400)
        time.sleep(0.35)

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
                txt = loc.inner_text(timeout=2500)
                if txt and len(txt.strip()) > 120:
                    return _clean_text(txt)
        except Exception:
            continue
    try:
        return _clean_text(page.inner_text("body"))
    except Exception:
        return ""
def _get_card_selector_for_url(url: str) -> str:
    """Verilen URL'nin domainine göre en doğru ilan kartı seçicisini atar."""
    if "bulldogjob.pl" in url:
        return "a[href*='/companies/jobs/']"
    elif "hiringcafe.com" in url:
        return "a[href*='/jobs/'], a[href*='/job/']"
    elif "nofluffjobs.com" in url:
        return "a[href*='/job/']"
    elif "theprotocol.it" in url:
        return "a[href*='/szczegoly/oferta/']"
    elif "europelanguagejobs.com" in url:
        return "a[href*='/job-offer/'], a[href*='/jobs/']"
    elif "talent.com" in url:
        return "a[href*='/view?id='], a.link-job-title"
    elif "hays.pl" in url:
        return "a[href*='/job-detail/'], a.job-title-link"
    elif "michaelpage.pl" in url:
        return "a[href*='/job-detail/']"
    elif "devire.pl" in url:
        return "a[href*='/job/'], .job-offer-title a"
    elif "randstad.pl" in url:
        return "a[href*='/job-offers/']"
    elif "amazon.jobs" in url:
        return "a[href*='/jobs/']"
    elif "pracuj.pl" in url:
        return "a[data-test='link-offer'], a[href*=',oferta,']"
    elif "linkedin.com" in url:
        return "a.job-card-container__link, a[data-control-name='job_card_click'], a[href*='/jobs/view/']"
    elif "indeed.com" in url:
        return "a[id^='job_'], a[class*='jcs-JobTitle']"
    elif "justjoin.it" in url:
        return "a[href*='/job-offer/']"
    elif "careersinpoland.com" in url:
        return "a[href*='/job/']"
    elif "jobleads.com" in url:
        return "a[href*='/job/']"
    elif "rocketjobs.pl" in url:
        return "a[href^='/oferta/']"
    elif "glassdoor.com" in url:
        return "a[data-test='job-title'], a[href*='/job-listing/']"
    elif "xpatjobs.com" in url:
        return "a[href*='/job/']"
    elif "revolut.com" in url:
        return "a[href*='/careers/position/'], a[href*='/positions/']"
    return "a"

# ==========================================
# 📋 TAM MANUEL İŞ LİNKLERİ MATRİSİ
# ==========================================
MANUAL_SEARCH_MATRIX = {
    "turkish": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dkrakow,gdansk,wroclaw,poznan,gdynia,lodz,lublin,katowice%20keyword%3Dturkish",
        "https://theprotocol.it/praca?kw=turkish",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=turkish",
        "https://www.hays.pl/en/job-search/turkish-jobs-in-poland-poland?q=Turkish&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Turkish%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Turkish%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Turkish%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/turkish/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6InR1cmtpc2giLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-turkish/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=turkish&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/turkish;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4475017826&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=turkish&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=turkish&l=Polska&radius=10&from=searchOnDesktopSerp%2Cwhereautocomplete&vjk=a78578ae21fb63b9",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=turkish&languages=en&sortBy=newest",
        "https://www.careersinpoland.com/jobs/language/english+turkish/city/remote+warszawa",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/turkish?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=turkish&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=turkish",
        "https://www.glassdoor.com/Job/poland-turkish-jobs-SRCH_IL.0,6_IN193_KO7,14.htm?fromAge=14&sortBy=date_desc",
        "https://poland.xpatjobs.com/search?ps=1&keyword=turkish&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=turkish"
    ],
    "operations": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Doperations",
        "https://theprotocol.it/praca?kw=operations",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=operations",
        "https://pl.talent.com/en/jobs?k=operations&l=Warsaw%2C+Mazovia&radius=5&id=631846930519436865",
        "https://www.hays.pl/en/job-search/operations-jobs-in-poland-poland?q=Operations&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Operations%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Operations%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Operations%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/operations",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6Im9wZXJhdGlvbnMiLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-operations/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?offset=0&result_limit=10&sort=recent&distanceType=Mi&radius=24km&latitude=52.2356&longitude=21.01037&loc_group_id=&loc_query=Poland&base_query=operations&city=&country=POL&region=&county=&query_options=&",
        "https://www.pracuj.pl/praca/turkish;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4473462047&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=operations&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=operations&l=Polska&from=searchOnDesktopSerp&vjk=80dd41d5d53855cd",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=operations&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/operations?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=operations&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=operations",
        "https://www.glassdoor.com/Job/poland-operations-jobs-SRCH_IL.0,6_IN193_KO7,17.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=operations&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=operations"
    ],
    "analyst": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Danalyst",
        "https://theprotocol.it/praca?kw=analyst",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=Analyst",
        "https://pl.talent.com/en/jobs?k=Analyst&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/analyst-jobs-in-poland-poland?q=Analyst&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Analyst%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Analyst%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Analyst%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/analyst/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6IkFuYWx5c3QiLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-analyst/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=analyst&loc_query=Poland&latitude=52.2356&longitude=21.01037&loc_group_id=&invalid_location=false&country=POL&city=&region=&county=",
        "https://www.pracuj.pl/praca/analyst;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4473462047&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=analyst&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=analyst&l=Polska&from=searchOnDesktopSerp&vjk=569eefbc59822d63",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=analyst&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/analyst?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=analyst&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=analyst",
        "https://www.glassdoor.com/Job/poland-analyst-jobs-SRCH_IL.0,6_IN193_KO7,14.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=analyst&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=analyst"
    ],
    "automation": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Dautomation",
        "https://theprotocol.it/praca?kw=automation",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=automation",
        "https://pl.talent.com/en/jobs?k=automation&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/automation-jobs-in-poland-poland?q=Automation&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Automation%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Automation%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Automation%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/automation/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6ImF1dG9tYXRpb24iLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-automation/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=automation&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/automation;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4473462047&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=automation&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=automation&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=automation&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/automation?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=automation&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=automation",
        "https://www.glassdoor.com/Job/poland-automation-jobs-SRCH_IL.0,6_IN193_KO7,17.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=automation&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=automation"
    ],
    "compliance": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Dcompliance",
        "https://theprotocol.it/praca?kw=compliance",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=compliance",
        "https://pl.talent.com/en/jobs?k=compliance&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/compliance-jobs-in-poland-poland?q=Compliance&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Compliance%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Compliance%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Compliance%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/compliance/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6ImNvbXBsaWFuY2UiLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-compliance/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=compliance&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/compliance;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4473462047&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=compliance&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=compliance&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=compliance&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/compliance?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=compliance&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=compliance",
        "https://www.glassdoor.com/Job/poland-compliance-jobs-SRCH_IL.0,6_IN193_KO7,17.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=compliance&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=compliance"
    ],
    "quality": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Dquality",
        "https://theprotocol.it/praca?kw=quality",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=quality",
        "https://pl.talent.com/en/jobs?k=quality&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/quality-jobs-in-poland-poland?q=Quality&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Quality%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Quality%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Quality%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/quality/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6InF1YWxpdHkiLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-quality/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=quality&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/quality;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4473462047&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=quality&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=quality&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=quality&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/quality?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=quality&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=quality",
        "https://www.glassdoor.com/Job/poland-quality-jobs-SRCH_IL.0,6_IN193_KO7,14.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=quality&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=quality"
    ],
    "risk": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Drisk",
        "https://theprotocol.it/praca?kw=risk",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=risk",
        "https://pl.talent.com/en/jobs?k=risk&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/risk-jobs-in-poland-poland?q=Risk&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Risk%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Risk%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Risk%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/risk/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6InJpc2siLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-risk/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=risk&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/risk;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4473462047&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=risk&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=risk&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=risk&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/risk?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=risk&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=risk",
        "https://www.glassdoor.com/Job/poland-risk-jobs-SRCH_IL.0,6_IN193_KO7,11.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=risk&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=risk"
    ],
    "data": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Ddata",
        "https://theprotocol.it/praca?kw=data",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=data",
        "https://pl.talent.com/en/jobs?k=data&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/data-jobs-in-poland-poland?q=Data&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Data%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Data%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Data%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/data/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6ImRhdGEiLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-data/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=data&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/data;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4473462047&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=data&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=data&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=data&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/data?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=data&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=data",
        "https://www.glassdoor.com/Job/poland-data-jobs-SRCH_IL.0,6_IN193_KO7,11.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=data&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=data"
    ],
    "junior": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Djunior",
        "https://theprotocol.it/praca?kw=junior",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=junior",
        "https://pl.talent.com/en/jobs?k=junior&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/junior-jobs-in-poland-poland?q=Junior&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Junior%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Junior%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Junior%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/junior/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6Imp1bmlvciIsImNpdGllcyI6W3siaWQiOiJPTCIsIm5hbWUiOiJQb2xza2EifSx7ImlkIjoiUEwxNDY1MDEwOTE4MTIzIiwibmFtZSI6IldhcnN6YXdhLCBNYXpvd2llY2tpZSJ9XSwicmVtb3RlIjpmYWxzZX0=",
        "https://www.randstad.pl/en/jobs/q-junior/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=junior&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/junior;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4473462047&f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=junior&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=junior&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=junior&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/junior?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=junior&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=junior",
        "https://www.glassdoor.com/Job/poland-junior-jobs-SRCH_IL.0,6_IN193_KO7,13.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=junior&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=junior"
    ],
    "programmer": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Dprogrammer",
        "https://theprotocol.it/praca?kw=programmer",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=programmer",
        "https://pl.talent.com/en/jobs?k=programmer&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/programmer-jobs-in-poland-poland?q=Programmer&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Programmer%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Programmer%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Programmer%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/programmer/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6InByb2dyYW1tZXIiLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-programmer/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=programmer&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/programmer;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=programmer&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=programmer&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=programmer&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/programmer?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=programmer&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=programmer",
        "https://www.glassdoor.com/Job/poland-programmer-jobs-SRCH_IL.0,6_IN193_KO7,17.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=programmer&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=programmer"
    ],
    "excel": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Dexcel",
        "https://theprotocol.it/praca?kw=excel",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=excel",
        "https://pl.talent.com/en/jobs?k=excel&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/excel-jobs-in-poland-poland?q=Excel&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Excel%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Excel%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Excel%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/excel/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6ImV4Y2VsIiwiY2l0aWVzIjpbeyJpZCI6IlBMIiwibmFtZSI6IlBvbHNrYSJ9LHsiaWQiOiJQTDE0NjUwMTA5MTgxMjMiLCJuYW1lIjoiV2Fyc3phd2EsIE1hem93aWVja2llIn1dLCJyZW1vdGUiOmZhbHNlfQ==",
        "https://www.randstad.pl/en/jobs/q-excel/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=excel&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/excel;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=excel&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=excel&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=excel&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/excel?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=excel&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=excel",
        "https://www.glassdoor.com/Job/poland-excel-jobs-SRCH_IL.0,6_IN193_KO7,12.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=excel&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=excel"
    ],
    "process": [
        "https://nofluffjobs.com/pl/warszawa?criteria=city%3Dgdansk,gdynia,lodz%20keyword%3Dprocess",
        "https://theprotocol.it/praca?kw=process",
        "https://europelanguagejobs.com/jobs-in-Poland?keywords=process",
        "https://pl.talent.com/en/jobs?k=process&l=Warsaw%2C+Mazovia&radius=5",
        "https://www.hays.pl/en/job-search/process-jobs-in-poland-poland?q=Process&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Process%20Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20Process%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20Process%20jobs%20now",
        "https://www.michaelpage.pl/en/jobs/process/poland",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6InByb2Nlc3MiLCJjaXRpZXMiOlt7ImlkIjoiUEwiLCJuYW1lIjoiUG9sc2thIn0seyJpZCI6IlBMMTQ2NTAxMDkxODEyMyIsIm5hbWUiOiJXYXJzemF3YSwgTWF6b3dpZWNraWUifV0sInJlbW90ZSI6ZmFsc2V9",
        "https://www.randstad.pl/en/jobs/q-process/mazowieckie/warszawa/remote/",
        "https://amazon.jobs/pl/search?base_query=process&loc_query=Poland&country=POL",
        "https://www.pracuj.pl/praca/process;kw/warszawa;wp?rd=30&wpl=true",
        "https://www.linkedin.com/jobs/search/?f_E=1%2C2&f_WT=2%2C3&geoId=105072130&keywords=process&origin=JOB_SEARCH_PAGE_SEARCH_BUTTON&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=process&l=Polska&from=searchOnDesktopSerp",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,internship&keyword=process&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland/q/process?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://pl.talent.com/en/jobs?k=process&l=Warszawa%2C+Masovian+Voivodeship&radius=100",
        "https://rocketjobs.pl/oferty-pracy/warszawa?radius=100&keyword=process",
        "https://www.glassdoor.com/Job/poland-process-jobs-SRCH_IL.0,6_IN193_KO7,14.htm",
        "https://poland.xpatjobs.com/search?ps=1&keyword=process&city=Warsaw&areas=28",
        "https://www.revolut.com/careers/?city=Poland+-+Remote&text=process"
    ],
    "extra_curated_sources": [
        "https://bulldogjob.pl/companies/jobs/s/city,Remote,Warszawa,Polska",
        "https://hiringcafe.com/ai-search/c/01m3z9fb1mnd2f5tv5me29ctx5",
        "https://www.revolut.com/careers/?city=Poland+-+Remote"
    ],
    "last_24_hours_angielski": [
        "https://nofluffjobs.com/pl/warszawa?criteria=jobLanguage%3Den",
        "https://theprotocol.it/filtry/umowa-o-prace;c/warszawa;wp",
        "https://europelanguagejobs.com/jobs-in-Warsaw-for-English-speakers",
        "https://www.hays.pl/en/job-search/in-poland-poland?q=&location=Poland,%20Poland&specialismId=&subSpecialismId=&locationf=&industryf=&sortType=0&jobType=-1&flexiWorkType=-1&payTypefacet=-1&minPay=-1&maxPay=-1&jobSource=HaysGCJ&searchPageTitle=Jobs%20in%20Poland,%20Poland%20%7C%20Hays%20Recruitment&searchPageDesc=Find%20the%20perfect%20job%20in%20Poland,%20Poland.%20Hays%20Recruitment%20can%20help%20you%20find%20the%20ideal%20role.%20Search%20for%20jobs%20now",
        "https://devire.pl/en/find-your-job/#s=eyJmaWx0ZXJzIjp7ImJyYW5jaGUiOltdLCJjYXRlZ29yeSI6W10sImxhbmd1YWdlIjpbXSwicmVnaW9uIjpbXSwiZWR1Y2F0aW9uIjpbXSwiam9iVHlwZSI6W10sInBvc2l0aW9uIjpbXSwic2FsYXJ5RnJvbSI6MCwic2FsYXJ5VG8iOjB9LCJwb3NpdGlvbiI6IiIsImNpdGllcyI6W3siaWQiOiJQTCIsIm5hbWUiOiJQb2xza2EifSx7ImlkIjoiUEwxNDY1MDEwOTE4MTIzIiwibmFtZSI6IldhcnN6YXdhLCBNYXpvd2llY2tpZSJ9XSwicmVtb3RlIjpmYWxzZX0=",
        "https://www.pracuj.pl/praca/warszawa;wp/ostatnich%207%20dni;p,7?rd=30&tc=0&ws=0&wpl=true",
        "https://www.linkedin.com/jobs/search/?currentJobId=4353923480&distance=10&f_E=2%2C3&f_JT=F&f_TPR=r86400&f_WT=2%2C1%2C3&geoId=102560051&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=DD",
        "https://pl.indeed.com/jobs?q=&l=Polska&fromage=7&sc=0kf%3Aattr%285QWDV%7CCF3CP%252COR%29%3B&from=searchOnDesktopSerp&vjk=6c75eae6cf3ace1c",
        "https://justjoin.it/job-offers/warszawa?employment-types=permanent&remote-work-options=hybrid,remote,office&working-times=full-time&experience-levels=junior,mid&published-date=7&languages=en&sortBy=newest",
        "https://www.jobleads.com/pl/jobs/l/Poland?filter_by_daysReleased=14&location_coordinates_radius=474205.0232836308&location_latitude=51.919438&location_longitude=19.145136&minSalary=90000",
        "https://www.glassdoor.com/Job/poland-turkish-jobs-SRCH_IL.0,6_IN193_KO7,14.htm?fromAge=30&sortBy=date_desc"
    ]
}


class JobScraper:
    def __init__(self):
        self.seen_jobs = _load_seen_jobs()
        self.search_matrix = MANUAL_SEARCH_MATRIX

    def _scrape_page(self, context, page_url: str, folder_name: str) -> list:
        domain = "/".join(page_url.split("/")[:3])
        site_label = domain.replace("https://", "").replace("www.", "").split(".")[0].upper()
        card_sel = _get_card_selector_for_url(page_url)

        jobs = []
        candidates = []
        local_seen = set()

        page = context.new_page()
        try:
            try:
                page.goto(page_url, timeout=22000, wait_until="domcontentloaded")
            except Exception:
                pass

            time.sleep(1.2)
            _handle_modals(page)
            _scroll_page(page, scrolls=4)

            elements = page.locator(card_sel).all()

            for el in elements:
                try:
                    href = el.get_attribute("href")
                    if not href:
                        continue

                    full_url = domain + href if href.startswith("/") else href
                    clean_url = full_url.split("?")[0]

                    # Çöp linkleri filtrele
                    if any(c in clean_url for c in ["/kategorie/", "/sprzedaz", "/marketing", "/budownictwo", "/edukacja", "/login", "/register"]):
                        continue

                    if "pracuj.pl" in clean_url and ",oferta," not in clean_url:
                        continue

                    if (clean_url in self.seen_jobs or 
                        clean_url in local_seen or 
                        clean_url == page_url or 
                        len(clean_url) < 20):
                        continue

                    title = el.inner_text().strip()
                    clean_title = title.split("\n")[0].strip() if title else "Job Opportunity"

                    local_seen.add(clean_url)
                    candidates.append({"url": full_url, "title": clean_title})
                except Exception:
                    continue

            candidates = candidates[:MAX_JOBS_PER_SITE]
            if candidates:
                print(f"      📍 [{site_label}] {len(candidates)} adet incelenecek yeni ilan kartı yakalandı.")

            for cand in candidates:
                detail_page = context.new_page()
                try:
                    detail_page.goto(cand["url"], timeout=16000, wait_until="domcontentloaded")
                    time.sleep(0.7)
                    _handle_modals(detail_page)

                    title_elem = detail_page.locator("h1").first
                    page_title = title_elem.inner_text().strip() if title_elem.count() > 0 else cand["title"]

                    full_text = _extract_page_text(detail_page)
                    if len(full_text) < 100:
                        continue

                    jobs.append({
                        "id": cand["url"],
                        "source_site": f"{folder_name.upper()} - {site_label}",
                        "title": page_title.replace("\n", " ")[:150],
                        "company": "See Link",
                        "city": "Warsaw / Remote",
                        "url": cand["url"],
                        "description": full_text,
                    })
                except Exception:
                    pass
                finally:
                    detail_page.close()
                    _sleep()

        except Exception as e:
            print(f"      ⚠️ URL taranırken hata ({domain}): {e}")
        finally:
            page.close()

        return jobs

    def fetch_jobs_site_by_site(self) -> dict:
        site_jobs = {}
        print("🌐 MANUEL LİNK MATRİSİ TABANLI DERİN TARAMA BAŞLATILDI...")

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

            for folder_name, urls in self.search_matrix.items():
                print(f"\n📂 ==========================================")
                print(f"📁 KLASÖR BAŞLATILDI: [{folder_name.upper()}] ({len(urls)} Link Taranıyor)")
                print(f"📂 ==========================================")

                folder_results = []
                for target_url in urls:
                    fetched = self._scrape_page(context, target_url, folder_name)
                    if fetched:
                        folder_results.extend(fetched)

                if folder_results:
                    site_jobs[folder_name] = folder_results

            browser.close()

        return site_jobs
