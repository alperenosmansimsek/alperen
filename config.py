import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# ==========================================
# 🔑 API & TELEGRAM CREDENTIALS
# ==========================================
GH_MODELS_TOKEN = os.getenv("GH_MODELS_TOKEN") or os.getenv("GITHUB_TOKEN", "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")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8711747765:AAFLXOKABz7ri6Zot3rJXqHQEaO0AThdjrE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1421665735")

# ==========================================
# ⚙️ FILTERING & PIPELINE PARAMETERS
# ==========================================
MIN_MATCH_SCORE = 85       # Katı filtreyi geçen kaliteli ilanlar için taban skor
REQUEST_DELAY = (0.5, 1.2) # İstekler arası bekleme

# ==========================================
# 🚫 LEHÇE ŞARTI ANAHTAR KELİMELERİ
# ==========================================
POLISH_REQUIREMENT_KEYWORDS = [
    "wymagany język polski", "polish required", "fluent polish", "polish language", 
    "b1 polish", "b2 polish", "c1 polish", "język polski - poziom", "znajomość języka polskiego",
    "bardzo dobra znajomość języka polskiego", "płynny polski"
]

# ==========================================
# 👤 ALPEREN ŞİMŞEK - GÜNCEL CV PROFİLİ (v2.0)
# ==========================================
USER_PROFILE = """
CANDIDATE IDENTITY & SKILLS:
- Full Name: Alperen Simsek
- Location: Warsaw, Poland
- Education:
  * M.Sc. in Computer Science (University of Economics and Computer Science in Warsaw - WSEI, Grade: 4.90/6)
  * B.Sc. in Mathematics (Uludag University, Grade: 3.02/4)
- Work Experience:
  * Amazon Corporate Services Poland (Compliance Associate, Oct 2024 - Oct 2026, 2 Years):
    - Rule-based automation scripts, data classification pipelines (99% accuracy across EU compliance).
    - Browser-based automation tool (Chrome Extension) reducing audit time by 98.3%.
    - Root cause analysis, SOP creation, mentoring 20+ team members, 2x Employee of the Month.
  * DenizBank (Intern, Bursa, Turkey): Operations workload reduction, Excel Macro/Pivot analysis.
- Tech Stack:
  * Core: Python (Automation & Data Processing), JavaScript (Browser Tools / DOM), Kotlin (Android Studio), HTML/CSS, SQL.
  * Tools & Cloud: AWS Cloud Foundations (Certified Cloud Practitioner), JIRA, PowerApps, Advanced Excel (VBA/Macros), MATLAB/Maple.
- Languages:
  * Turkish: Native (C2)
  * English: Fluent (C1)
- Target Roles:
  * Compliance Operations / Compliance Analyst / Regulatory Compliance
  * Risk Operations / Risk Analyst 
  * Operations Analyst / Process Improvement Specialist / Workflow Automation Specialist
  * QA Automation / Junior Python Developer / Turkish Language Specialist
- Excluded Skills (DO NOT MATCH):
  * Java, C++, C#, .NET, Spring, Angular, React, Vue, Flutter, Golang, Rust, PHP, SAP, Salesforce.
  * Heavy Polish language requirements (C1/B2 mandatory).
  * Lead / Director roles requiring 3+ years of experience.
"""
