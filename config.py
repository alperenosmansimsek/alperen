import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# 🔑 API & TELEGRAM CREDENTIALS
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8711747765:AAFLXOKABz7ri6Zot3rJXqHQEaO0AThdjrE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1421665735")

# ==========================================
# ⚙️ FILTERING & PIPELINE PARAMETERS
# ==========================================
MIN_MATCH_SCORE = 70       # Minimum uyum puanı (0-100)
REQUEST_DELAY = (0.8, 2.0) # İstekler arası bekleme süresi

# ==========================================
# 🏢 FİRMA AYARLARI
# ==========================================
BLACK_LIST_COMPANIES = []
REFERRAL_COMPANIES = ["ecovadis", "accenture", "amazon", "google", "standard chartered"]

# ==========================================
# 🚫 LEHÇE ŞARTI ANAHTAR KELİMELERİ
# ==========================================
POLISH_REQUIREMENT_KEYWORDS = [
    "wymagany język polski", "polish required", "fluent polish", 
    "b2 polish", "c1 polish", "język polski - poziom", "znajomość języka polskiego"
]

# ==========================================
# ==========================================
USER_PROFILE = """
CANDIDATE IDENTITY & SKILLS: 
- Education: M.Sc. in Computer Science (WSEI Warsaw), B.Sc. in Mathematics (Uludag University).
- Languages: English (Fluent C1), Turkish (Native C2), Polish (A1 - Basic), German (A1 - Basic).
- Current Role: Amazon Corporate Services Poland (Senior Compliance Associate - Risk, Auditing, Workflow Optimization).
- Tech Stack: Python (Data & Automation), Kotlin (Android Studio), JavaScript, HTML/CSS, AWS (Certified Cloud Practitioner), SQL, Advanced Excel (VBA/Macros).
- Target Roles: Compliance & Risk Specialist, Operations Analyst, Process Improvement Specialist, Turkish Language Roles, Junior Software / Android Developer, QA / Automation Specialist.
- Excluded Tech: Java, C++, C#, .NET, Spring, Angular, React, Flutter, Go, Rust, PHP, SAP, Salesforce.
"""
