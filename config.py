# config.py

# information for GROQ API and Telegram Bot
GROQ_API_KEY = "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"
RAPIDAPI_KEY = "ea15e6fa72mshcfa7ba54a375736p1ce629jsnd90b8ecc55c"
TELEGRAM_BOT_TOKEN = "8711747765:AAFLXOKABz7ri6Zot3rJXqHQEaO0AThdjrE"
TELEGRAM_CHAT_ID = "1421665735"

# Filtering Parameters
MIN_MATCH_SCORE = 70  # Minimum match score for job postings (0-100)
 
REQUEST_DELAY = (1.0, 2.5)      # Detay sayfalari arasi rastgele bekleme (saniye, min-max)
 
# Blacklisted Companies (Jobs from these companies will be dropped)
BLACK_LIST_COMPANIES = ["amazon", "aws", "ring", "twitch", "audible", "buy with prime"]
 
# Referral Companies (Jobs from these companies will be prioritized)
REFERRAL_COMPANIES = ["ecovadis", "accenture"]
 
# Keywords indicating that Polish language proficiency is required for the job
POLISH_REQUIREMENT_KEYWORDS = [
    "wymagany język polski", "polish required", "fluent polish", 
    "b2 polish", "c1 polish", "język polski - poziom", "znajomość języka polskiego"
]
 
USER_PROFILE = """
CANDIDATE IDENTITY & SKILLS:
- Status: University Graduate (Mathematics Degree, CS Master's background) - NOT a current student.
- Languages: English (Fluent C1 - Professional Corporate Level), Turkish (Native Speaker). CANNOT speak Polish (A1) or other foreign languages.
- Current Role: Amazon Corporate Services Poland (Compliance & Risk Operations) - Handling process workflows, risk assessments, data classification, and automation scripts.
- Technical Skills: Python, JavaScript, Kotlin / Android Development, AWS Certified, Data Analysis, SQL concepts, Automation.
- Target Role Spectrum (Tech & Non-Tech): Turkish Language Roles, Compliance & Risk Specialist, Operations Analyst, Business/Data Analyst, Customer Success / Technical Support, QA Automation, Junior Software / Mobile Developer.
- Excluded Skills (NOT possessed): Java, C++, C#, .NET, Go, Rust, React, Angular, PHP, Salesforce, SAP.
"""