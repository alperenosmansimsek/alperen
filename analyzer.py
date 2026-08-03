# analyzer.py
import json
import time
import re
from groq import Groq
from config import GROQ_API_KEY, USER_PROFILE

class JobAnalyzer:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = "llama-3.1-8b-instant"

    def is_hard_rejected_by_code(self, text: str) -> tuple[bool, str]:
        """Python seviyesinde anında eleme yapan kurşun geçirmez filtre."""
        text_lower = text.lower()

        # 1. LEHÇE ÖZEL KARAKTERLER (Diakritikler) - İlandan tek bir Lehçe harf bile çıkarsa REJECT
        polish_chars = re.findall(r'[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', text)
        if len(polish_chars) > 0:
            return True, f"HARD REJECT: Contains Polish specific characters ({len(polish_chars)} chars found)."

        # 2. ÖĞRENCİ / STAJYER FİLTRESİ
        student_terms = [r'\bintern\b', r'\binternship\b', r'\bstudent\b', r'\btrainee\b', r'\bpraktykant\b', r'\bstaż\b']
        for term in student_terms:
            if re.search(term, text_lower):
                clean_term = term.replace('\\b', '')
                return True, f"HARD REJECT: Student/Intern position ({clean_term})."

        # 3. İNGİLİZCE & TÜRKÇE HARİCİ TÜM YABANCI DİLLER
        banned_languages = [
            r'\bgerman\b', r'\bdeutsch\b', r'\bfrench\b', r'\bitalian\b', r'\bspanish\b', 
            r'\bdutch\b', r'\bswedish\b', r'\bnorwegian\b', r'\bdanish\b', r'\bpolish\b'
        ]
        for lang in banned_languages:
            if re.search(lang, text_lower):
                clean_lang = lang.replace('\\b', '')
                return True, f"HARD REJECT: Requires foreign language ({clean_lang})."

        # 4. BİLMEDİĞİN YAZILIM DİLLERİ VE TEKNOLOJİ KARA LİSTESİ
        banned_technologies = [
            r'\bc\+\+\b', r'\bc#\b', r'\bcpp\b', r'\bjava\b', r'\bjava8\b', r'\bjava11\b', r'\bjava17\b',
            r'\bspring\b', r'\bspring boot\b', r'\bhibernate\b', r'\bmaven\b', r'\bgradle\b',
            r'\bgolang\b', r'\bgo lang\b', r'\brust\b', r'\bphp\b', r'\bruby\b', r'\bscala\b',
            r'\bswift\b', r'\bdart\b', r'\bflutter\b', r'\breact native\b', r'\bios developer\b',
            r'\bangular\b', r'\breact\b', r'\breactjs\b', r'\bvue\b', r'\bvuejs\b', r'\bsvelte\b',
            r'\b\.net\b', r'\bdotnet\b', r'\basp\.net\b', r'\blaravel\b', r'\bsymfony\b',
            r'\bsalesforce\b', r'\bsap\b', r'\babap\b', r'\bservicenow\b', r'\bworkday\b'
        ]
        for tech in banned_technologies:
            if re.search(tech, text_lower):
                clean_tech = tech.replace('\\b', '').replace('\\', '')
                return True, f"HARD REJECT: Requires unpossessed tech ({clean_tech})."

        return False, ""

    def evaluate_job(self, job: dict, retries: int = 3) -> dict:
        combined_text = f"{job['title']} {job['description']}"

        # 1. KATI KOD FİLTRESİ
        is_rejected, reject_reason = self.is_hard_rejected_by_code(combined_text)
        if is_rejected:
            return {
                "match_score": 0,
                "candidate_summary": "Filtered by Strict Code Rules.",
                "reason": reject_reason,
                "recommended_focus": "Skip - Rule Violation"
            }

        # 2. GROQ AI EVALUATION: PUANLAMA SİSTEMİ (0 - 100)
        system_instruction = f"""
You are a career matching assistant. Evaluate job openings for the candidate.

CANDIDATE FULL PROFILE:
{USER_PROFILE}

EVALUATION SCORING RULES:
1. Languages: Candidate knows ONLY English (Fluent) and Turkish (Native). NO Polish/German/French.
2. Degree & Status: Graduate (Math/CS Master background). NOT a student/intern.
3. Good Match Roles (Score 80-100%): Compliance & Risk Ops (Amazon background), Data/Business Analyst, Operations, Turkish Speaker Specialist, QA, Junior Android/Kotlin, or Python/AWS Support.
4. Poor Match Roles (Score < 70%): Lacks hard required skills or requires unpossessed software stacks.

Return ONLY a valid JSON object matching this schema (no markdown):
{{
  "candidate_summary": "<1 short sentence on candidate fit>",
  "match_score": <integer 0-100>,
  "reason": "<2 concise sentences explaining the score>",
  "recommended_focus": "<1 key bullet point strategy>"
}}
"""

        prompt = f"""
JOB OPENING TO EVALUATE:
Title: {job['title']}
Description: {job['description']}
"""

        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model=self.model,
                    temperature=0.0,
                    response_format={"type": "json_object"}
                )

                clean_text = response.choices[0].message.content.strip()
                result = json.loads(clean_text)

                return {
                    "match_score": result.get("match_score", 0),
                    "candidate_summary": result.get("candidate_summary", ""),
                    "reason": result.get("reason", "No reason provided."),
                    "recommended_focus": result.get("recommended_focus", "N/A")
                }

            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate_limit" in err_msg:
                    time.sleep(15)
                else:
                    break

        return {
            "match_score": 0, 
            "candidate_summary": "N/A", 
            "reason": "Evaluation Error", 
            "recommended_focus": "N/A"
        }