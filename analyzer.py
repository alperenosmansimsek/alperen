import re

class JobAnalyzer:
    def __init__(self):
        pass

    def is_hard_rejected_by_code(self, text: str) -> tuple[bool, str]:
        text_lower = text.lower()

        if any(w in text_lower for w in ["cloudflare", "security check", "bot verification", "captcha"]):
            return True, "HARD REJECT: Anti-bot verification page."

        polish_chars = re.findall(r'[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]', text)
        if len(polish_chars) > 15:
            return True, f"HARD REJECT: Polish language job ({len(polish_chars)} chars)."

        student_terms = [r'\bintern\b', r'\binternship\b', r'\bstudent\b', r'\btrainee\b', r'\bpraktykant\b', r'\bstaż\b']
        for term in student_terms:
            if re.search(term, text_lower):
                clean_term = term.replace(chr(92) + 'b', '')
                return True, f"HARD REJECT: Student/Intern position ({clean_term})."

        banned_languages = [r'\bgerman\b', r'\bdeutsch\b', r'\bfrench\b', r'\bitalian\b', r'\bspanish\b', r'\bdutch\b']
        for lang in banned_languages:
            if re.search(lang, text_lower):
                clean_lang = lang.replace(chr(92) + 'b', '')
                return True, f"HARD REJECT: Requires foreign language ({clean_lang})."

        banned_tech = [
            r'\bc\+\+\b', r'\bc#\b', r'\bcpp\b', r'\bjava\b', r'\bspring\b', r'\bgolang\b',
            r'\brust\b', r'\bphp\b', r'\bruby\b', r'\bflutter\b', r'\bangular\b', r'\breact\b', 
            r'\b\.net\b', r'\bsalesforce\b', r'\bsap\b'
        ]
        
        for tech in banned_tech:
            if re.search(tech, text_lower):
                clean_tech = tech.replace(chr(92) + 'b', '')
                return True, f"HARD REJECT: Engineering tech stack ({clean_tech})."

        return False, ""

    def evaluate_job(self, job: dict) -> dict:
        title = job.get('title', '')
        desc = job.get('description', '')
        combined_text = f"{title} {desc}".lower()

        is_rejected, reject_reason = self.is_hard_rejected_by_code(combined_text)
        if is_rejected:
            return {
                "match_score": 0,
                "candidate_summary": "Filtered by rule.",
                "reason": reject_reason,
                "recommended_focus": "Skip"
            }

        score = 50
        matches = []
        matched_roles = []

        # 1. Hedef Rol Eşleşmeleri (+20 Puan)
        target_roles = [
            "compliance", "risk", "analyst", "operations", "data", "operations analyst", 
            "process improvement", "qa automation", "test automation", 
            "turkish", "data analyst", "business analyst", "software engineer", 
            "android developer", "kotlin developer", "python developer", "junior developer"
        ]
        
        for r in target_roles:
            if r in title.lower():
                score += 20
                matched_roles.append(r.title())
                break

        # 2. Yetkinlik ve Teknoloji Eşleşmeleri (+10 her biri)
        tech_stack = {
            "python": "Python Automation",
            "kotlin": "Kotlin / Android",
            "javascript": "JavaScript / Extension",
            "excel": "Advanced Excel & Macros",
            "turkish": "Native Turkish",
            "automation": "Workflow Automation",
            "compliance": "Regulatory Compliance",
            "risk": "Risk Assessment"
        }

        for k, label in tech_stack.items():
            if re.search(rf'\b{k}\b', combined_text):
                score += 10
                matches.append(label)

        # 3. Kıdem Seviyesi Kontrolü
        if any(s in title.lower() for s in [ "lead", "head of", "director", "manager"]):
            score -= 5
        elif any(j in title.lower() for j in ["senior", "junior", "associate", "specialist", "analyst"]):
            score += 5

        score = max(0, min(score, 98))

        role_str = matched_roles[0] if matched_roles else "Target Domain"
        tech_str = ", ".join(matches[:4]) if matches else "Core Analytical Skills"

        summary = f"Strong alignment with {role_str} profile."
        reason = f"Position matches key background areas: {tech_str}. Fits target career track."
        focus = f"Highlight hands-on experience in {tech_str} and relevant project deliverables."

        return {
            "match_score": score,
            "candidate_summary": summary,
            "reason": reason,
            "recommended_focus": focus
        }
