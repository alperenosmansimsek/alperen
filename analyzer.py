import os
import re
import json
import requests
from config import GH_MODELS_TOKEN, USER_PROFILE

ENDPOINT = "https://models.inference.ai.azure.com/chat/completions"
MODEL_NAME = "meta/llama-3.3-70b-instruct"

class JobAnalyzer:
    def __init__(self):
        self.token = GH_MODELS_TOKEN

    def is_hard_rejected_by_code(self, title: str, text: str) -> tuple[bool, str]:
        combined = f"{title} {text}".lower()

        # 1. Bot doğrulama sayfaları
        if any(w in combined for w in ["cloudflare", "security check", "bot verification", "captcha"]):
            return True, "Anti-bot verification page."

        # 2. Lehçe İlan Filtresi (A1 seviyesinde olunduğu için ağır Lehçe elenir)
        polish_chars = re.findall(r'[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', text)
        if len(polish_chars) > 6:
            return True, f"Polish language job ({len(polish_chars)} chars)."

        # 3. Öğrenci / Stajyer Pozisyonları
        student_terms = [r'\bintern\b', r'\binternship\b', r'\bstudent\b', r'\btrainee\b', r'\bpraktykant\b', r'\bstaż\b']
        for term in student_terms:
            if re.search(term, combined):
                clean_term = term.replace(r'\b', '')
                return True, f"Student/Intern position ({clean_term})."

        # 4. Bilinmeyen Yabancı Diller (Türkçe ve İngilizce dışındakiler)
        banned_languages = [
            r'\bgerman\b', r'\bdeutsch\b', r'\bfrench\b', r'\bfrançais\b',
            r'\bspanish\b', r'\bespañol\b', r'\bitalian\b', r'\bdutch\b',r'\bnederlands\b', r'\bswedish\b', r'\bnorwegian\b', r'\bdanish\b',
            r'\bfinnish\b', r'\brussian\b', r'\brusskiy\b', r'\bchinese\b', r'\bmandarin\b', r'\bjapanese\b', r'\bkorean\b', r'\barabic\b', r'\bharbic\b', r'\bportuguese\b', r'\bportuguês\b', r'\bpolish\b', r'\bjęzyk polski\b', r'\bpolski\b'
        ]
        for lang in banned_languages:
            if re.search(lang, combined):
                clean_lang = lang.replace(r'\b', '')
                return True, f"Requires foreign language ({clean_lang})."


        # 6. Bilinmeyen Mühendislik Teknolojileri
        banned_tech = [
            r'\bc\+\+\b', r'\bc#\b', r'\bcpp\b', r'\bjava\b', r'\bspring\b', r'\bgolang\b',
            r'\brust\b', r'\bphp\b', r'\bruby\b', r'\bflutter\b', r'\bangular\b', r'\breact\b', 
            r'\b\.net\b', r'\bsalesforce\b', r'\bsap\b'
        ]
        for tech in banned_tech:
            if re.search(tech, combined):
                clean_tech = tech.replace(r'\b', '')
                return True, f"Unpossessed tech stack ({clean_tech})."

        return False, ""

    def evaluate_rule_based(self, title: str, combined_text: str) -> dict:
        """AI yanıt vermezse veya token yoksa çalışan hassas deterministik motor."""
        score = 50
        matches = []
        matched_roles = []

        # 1. Alperen İçin Hedef Rol Eşleşmeleri (+25 Puan)
        target_roles = [
            "compliance", "risk", "aml", "kyc", "operations analyst", "operations",
            "process improvement", "process automation", "qa automation", "test automation", 
            "turkish", "data analyst", "business analyst", "software engineer", 
            "android developer", "kotlin developer", "python developer", "junior developer"
        ]
        for r in target_roles:
            if r in title.lower():
                score += 25
                matched_roles.append(r.title())
                break

        # 2. Güncel CV Yetkinlik Eşleşmeleri (+5 her biri)
        tech_stack = {
            "python": "Python Automation",
            "kotlin": "Kotlin / Android",
            "javascript": "JavaScript / Chrome Extension",
            "aws": "AWS Cloud Foundations",
            "sql": "SQL Database",
            "jira": "JIRA Workflow",
            "powerapps": "PowerApps",
            "excel": "Advanced Excel & Macros",
            "turkish": "Native Turkish",
            "compliance": "Regulatory Compliance",
            "risk": "Risk Operations",
            "automation": "Workflow Automation",
            "audit": "Quality & Audit Readiness"
        }

        for k, label in tech_stack.items():
            if re.search(rf'\b{k}\b', combined_text):
                score += 5
                matches.append(label)

        # 3. Pozisyon Seviyesi Uyumu
        if any(j in title.lower() for j in ["junior", "associate", "specialist", "analyst"]):
            score += 10

        score = max(0, min(score, 99))

        role_str = matched_roles[0] if matched_roles else "Target Operational Role"
        tech_str = ", ".join(matches[:4]) if matches else "Core Analytical Background"

        return {
            "match_score": score,
            "candidate_summary": f"Strong alignment with {role_str} profile.",
            "reason": f"Matches key strengths: {tech_str}. Aligns with Amazon compliance and automation background.",
            "recommended_focus": f"Highlight Amazon audit workflows, Python/JS tools, and {tech_str} deliverables."
        }

    def evaluate_job(self, job: dict) -> dict:
        title = job.get('title', '')
        desc = job.get('description', '')
        combined_text = f"{title} {desc}".lower()

        # Aşama 1: Katı Kod Filtresi (Maliyetsiz, anlık)
        is_rejected, reject_reason = self.is_hard_rejected_by_code(title, combined_text)
        if is_rejected:
            return {
                "match_score": 0,
                "candidate_summary": "Filtered by rule.",
                "reason": reject_reason,
                "recommended_focus": "Skip"
            }

        # Aşama 2: AI Analizi (GitHub Models - Llama-3.3-70B)
        if self.token:
            prompt = f"""
Sen tarafsız ve analitik bir işe alım danışmanısın. Aşağıdaki adayı iş ilanıyla karşılaştır.

ADAY PROFİLİ:
{USER_PROFILE}

İŞ İLANI:
Başlık: {title}
Şirket: {job.get('company')}
Açıklama: {desc[:2500]}

Yalnızca aşağıdaki JSON formatında yanıt ver:
{{
  "candidate_summary": "<Adayın profile uyumu hakkında 1 kısa cümle>",
  "match_score": <0 ile 100 arasında tamsayı>,
  "reason": "<Pozisyonun neden uyduğunu veya eksik kalan yönleri belirten 2 net cümle>",
  "recommended_focus": "<CV veya başvuruda öne çıkarılması gereken 1 kilit madde>"
}}
"""
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}"
            }
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "model": MODEL_NAME,
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }

            try:
                res = requests.post(ENDPOINT, headers=headers, json=payload, timeout=20)
                if res.status_code == 200:
                    raw_data = res.json()["choices"][0]["message"]["content"]
                    result = json.loads(raw_data)
                    return {
                        "match_score": int(result.get("match_score", 0)),
                        "candidate_summary": result.get("candidate_summary", ""),
                        "reason": result.get("reason", ""),
                        "recommended_focus": result.get("recommended_focus", "")
                    }
            except Exception as e:
                print(f"      ⚠️ AI API çağrısı başarısız oldu ({e}), kural motoruna geçiliyor...")

        # Aşama 3: Fallback (Deterministik Motor)
        return self.evaluate_rule_based(title, combined_text)
