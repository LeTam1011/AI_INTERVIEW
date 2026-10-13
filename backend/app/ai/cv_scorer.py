
import re
import unicodedata
from typing import Any


WEIGHTS = {
    "skill_match": 30,
    "experience_match": 20,
    "project_match": 20,
    "education": 10,
    "keyword_match": 10,
    "cv_quality": 10,
}


# Skill synonyms and common technology naming variants.
SKILL_SYNONYMS = {
    "javascript": ["javascript", "js"],
    "typescript": ["typescript", "ts"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "node.js": ["node.js", "nodejs", "node js"],
    "react": ["react", "react.js", "reactjs"],
    "vue.js": ["vue.js", "vuejs", "vue js"],
    "next.js": ["next.js", "nextjs", "next js"],
    "nuxt.js": ["nuxt.js", "nuxtjs", "nuxt js"],
    "c#": ["c#", "c sharp", "csharp"],
    "c++": ["c++", "cpp"],
    ".net": [".net", "dotnet", "dot net"],
    "asp.net": ["asp.net", "asp net", "aspnet"],
    "golang": ["golang", "go language"],
    "amazon web services": ["aws", "amazon web services"],
    "google cloud platform": ["gcp", "google cloud platform"],
    "microsoft azure": ["azure", "microsoft azure"],
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "dl"],
    "natural language processing": [
        "natural language processing", "nlp"
    ],
    "artificial intelligence": ["artificial intelligence", "ai"],
    "continuous integration": ["continuous integration", "ci"],
    "continuous deployment": ["continuous deployment", "cd"],
    "continuous integration and continuous deployment": [
        "ci/cd",
        "continuous integration and continuous deployment",
        "continuous integration continuous deployment",
    ],
    "rest api": ["rest api", "restful api", "restful services"],
    "postgres database": ["postgres database", "postgresql database"],
    "structured query language": ["sql", "structured query language"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "spring boot": ["spring boot", "springboot"],
    "microsoft sql server": ["sql server", "microsoft sql server", "mssql"],
    "kubernetes": ["kubernetes", "k8s"],
    "docker": ["docker"],
}





LEVEL_MIN_YEARS = {
    "intern": 0,
    "fresher": 0,
    "junior": 1,
    "middle": 3,
    "senior": 5,
}

# Từ phổ biến không mang nhiều ý nghĩa khi so sánh CV với JD.
STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "have",
    "will", "you", "your", "our", "are", "was", "were", "has",
    "can", "not", "all", "any", "job", "work", "working", "team",
    "experience", "skills", "ability", "knowledge", "using",
    "cua", "va", "cho", "voi", "cac", "mot", "trong", "duoc",
    "co", "la", "ung", "vien", "kinh", "nghiem", "ky", "nang",
    "thuc", "hien", "tham", "gia", "xay", "dung",
}

SECTION_ALIASES = {
    "projects": [
        "project", "projects", "du an", "personal project",
        "academic project",
    ],
    "experience": [
        "experience", "work history", "employment", "kinh nghiem",
        "internship", "internships", "thuc tap",
    ],
    "education": [
        "education", "academic", "hoc van", "university",
        "college", "degree", "giao duc",
    ],
    "skills": [
        "skills", "technical skills", "technologies", "ky nang",
        "cong nghe",
    ],
}


def _normalize(text: str) -> str:
    """Lowercase, remove accents and normalize punctuation/spacing."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9+#.\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _build_skill_alias_index() -> dict[str, set[str]]:
    """Map every normalized alias to its canonical skill group."""
    index: dict[str, set[str]] = {}

    for canonical, aliases in SKILL_SYNONYMS.items():
        group = {_normalize(canonical)}
        group.update(_normalize(alias) for alias in aliases)

        for alias in group:
            index.setdefault(alias, set()).update(group)

    return index


_SKILL_ALIAS_INDEX = _build_skill_alias_index()


def _skill_variants(skill: str) -> set[str]:
    """Return normalized variants for a skill name."""
    normalized = _normalize(skill)
    if not normalized:
        return set()

    return _SKILL_ALIAS_INDEX.get(normalized, {normalized})


def _matches_skill(text: str, required_skill: str) -> bool:
    """True if the CV contains the requested skill or a known synonym."""
    return any(
        _contains_term(text, variant)
        for variant in _skill_variants(required_skill)
    )


def _as_text(value: Any) -> str:
    """Convert profile fields to searchable text without assuming a fixed schema."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_as_text(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_as_text(v) for v in value)
    return str(value)


def _unique_strings(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    result = []
    seen = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            continue
        key = _normalize(value)
        if key and key not in seen:
            seen.add(key)
            result.append(value.strip())
    return result


def _contains_term(text: str, term: str) -> bool:
    """Match a phrase as a whole phrase, avoiding simple substring false positives."""
    normalized_text = f" {_normalize(text)} "
    normalized_term = _normalize(term)
    if not normalized_term:
        return False
    return f" {normalized_term} " in normalized_text


def _section_text(text: str, section: str) -> str:
    """
    Approximate section extraction from common CV headings.
    Falls back to the whole CV if headings cannot be identified.
    """
    normalized = _normalize(text)
    aliases = SECTION_ALIASES[section]
    positions = []

    for alias in aliases:
        match = re.search(rf"(?<!\w){re.escape(_normalize(alias))}(?!\w)", normalized)
        if match:
            positions.append(match.start())

    if not positions:
        return ""

    start = min(positions)
    other_positions = []
    for other_section, other_aliases in SECTION_ALIASES.items():
        if other_section == section:
            continue
        for alias in other_aliases:
            match = re.search(
                rf"(?<!\w){re.escape(_normalize(alias))}(?!\w)",
                normalized[start + 1:],
            )
            if match:
                other_positions.append(start + 1 + match.start())

    end = min(other_positions) if other_positions else len(normalized)
    return normalized[start:end]


def _score_ratio(matched: int, total: int) -> float:
    """Return a score between 0 and 100; no requirements means neutral, not zero."""
    if total <= 0:
        return 100.0
    return round(100 * matched / total, 2)


def score_cv(
    *,
    resume_text: str,
    candidate_profile: dict[str, Any] | None,
    job_title: str,
    job_description: str,
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
    responsibilities: list[str] | None = None,
    career_level: str = "junior",
) -> dict[str, Any]:
    """
    Deterministic, explainable CV-to-JD scoring.
    This is a first-pass heuristic, not a trained machine-learning model.
    """
    profile_text = _as_text(candidate_profile)
    cv_text = f"{resume_text or ''}\n{profile_text}".strip()

    if not cv_text:
        raise ValueError("CV has no extracted text to score")

    normalized_cv = _normalize(cv_text)
    normalized_jd = _normalize(
        f"{job_title}\n{job_description}\n"
        f"{_as_text(required_skills)}\n"
        f"{_as_text(preferred_skills)}\n"
        f"{_as_text(responsibilities)}"
    )

    required = _unique_strings(required_skills)
    preferred = _unique_strings(preferred_skills)
    responsibility_items = _unique_strings(responsibilities)


    matched_required = [
        skill for skill in required
        if _matches_skill(normalized_cv, skill)
    ]
    missing_required = [
        skill for skill in required
        if skill not in matched_required
    ]
    matched_preferred = [
        skill for skill in preferred
        if _matches_skill(normalized_cv, skill)
    ]
    missing_preferred = [
        skill for skill in preferred
        if skill not in matched_preferred
    ]


    # Skill match: required skills have greater importance than preferred skills.
    skill_parts = []
    if required:
        skill_parts.append((_score_ratio(len(matched_required), len(required)), 0.8))
    if preferred:
        skill_parts.append((_score_ratio(len(matched_preferred), len(preferred)), 0.2))

    if skill_parts:
        skill_score = round(
            sum(score * weight for score, weight in skill_parts)
            / sum(weight for _, weight in skill_parts),
            2,
        )
    else:
        # Do not give a perfect skill score if the JD has no explicit skill list.
        # Use technical-looking terms shared by the CV and job description instead.
        jd_terms = {
            token for token in re.findall(r"[a-z][a-z0-9+#.-]{1,}", normalized_jd)
            if token not in STOP_WORDS
        }
        cv_terms = set(re.findall(r"[a-z][a-z0-9+#.-]{1,}", normalized_cv))
        overlap = jd_terms & cv_terms
        skill_score = _score_ratio(len(overlap), min(len(jd_terms), 10)) if jd_terms else 0
        skill_score = min(skill_score, 100)

    # Experience match uses the requested career level and evidence in the CV.
    level = str(career_level).lower().split(".")[-1]
    required_years = LEVEL_MIN_YEARS.get(level, LEVEL_MIN_YEARS["junior"])
    year_values = [
        int(value) for value in re.findall(
            r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\b", normalized_cv
        )
        if 0 <= int(value) <= 50
    ]
    explicit_years = max(year_values, default=0)

    experience_section = _section_text(cv_text, "experience")
    has_experience_section = bool(experience_section)
    experience_evidence = has_experience_section or bool(
        re.search(r"\b(intern|internship|developer|engineer|employment|thuc tap)\b",
                  normalized_cv)
    )

    if required_years == 0:
        experience_score = 100.0 if experience_evidence else 65.0
    elif explicit_years >= required_years:
        experience_score = 100.0
    elif explicit_years > 0:
        experience_score = round(100 * explicit_years / required_years, 2)
    elif experience_evidence:
        experience_score = 60.0
    else:
        experience_score = 25.0

    # Project match: check for a project section and overlap with responsibilities.
    project_section = _section_text(cv_text, "projects")
    if responsibility_items:
        matched_responsibilities = [
            item for item in responsibility_items
            if _contains_term(project_section or cv_text, item)
        ]
        project_overlap = _score_ratio(
            len(matched_responsibilities), len(responsibility_items)
        )
        project_score = round(
            0.7 * project_overlap + 30.0 * bool(project_section), 2
        )
    else:
        project_score = 75.0 if project_section else 35.0

    project_score = min(100.0, project_score)

    # Education: look for an education section and common degree keywords.
    education_section = _section_text(cv_text, "education")
    education_terms = [
        "bachelor", "bachelors", "degree", "university", "college",
        "computer science", "information technology", "cử nhân",
        "đại học", "cao đẳng", "kỹ thuật phần mềm",
    ]
    education_evidence = any(
        _contains_term(education_section or cv_text, term)
        for term in education_terms
    )
    education_score = (
        100.0 if education_section and education_evidence
        else 65.0 if education_section or education_evidence
        else 25.0
    )

    # Keyword match: overlap between meaningful JD terms and CV terms.
    jd_tokens = {
        token for token in re.findall(r"[a-z][a-z0-9+#.-]{1,}", normalized_jd)
        if token not in STOP_WORDS
    }
    cv_tokens = set(re.findall(r"[a-z][a-z0-9+#.-]{1,}", normalized_cv))
    keyword_candidates = jd_tokens - {
        _normalize(s) for s in required + preferred
    }
    matched_keywords = sorted(keyword_candidates & cv_tokens)
    keyword_score = _score_ratio(
        len(matched_keywords), min(len(keyword_candidates), 20)
    ) if keyword_candidates else 100.0
    keyword_score = min(keyword_score, 100.0)

    # CV quality: transparent structure and length heuristics.
    word_count = len(re.findall(r"\b[\w+#.-]+\b", cv_text))
    headings_found = [
        section for section in SECTION_ALIASES
        if _section_text(cv_text, section)
    ]
    quality_score = 0.0
    quality_score += 35 if word_count >= 150 else 20 if word_count >= 70 else 5
    quality_score += min(40, len(headings_found) * 10)
    quality_score += 15 if re.search(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", cv_text, re.I) else 0
    quality_score += 10 if re.search(r"\bhttps?://|linkedin\.com|github\.com", cv_text, re.I) else 0
    quality_score = min(100.0, quality_score)

    raw_scores = {
        "skill_match": skill_score,
        "experience_match": experience_score,
        "project_match": project_score,
        "education": education_score,
        "keyword_match": keyword_score,
        "cv_quality": quality_score,
    }

    breakdown = {
        key: {
            "score": round(value, 2),
            "weight": WEIGHTS[key],
            "weighted_score": round(value * WEIGHTS[key] / 100, 2),
        }
        for key, value in raw_scores.items()
    }
    overall_score = round(
        sum(item["weighted_score"] for item in breakdown.values()), 2
    )

    strengths = []
    improvements = []

    if matched_required:
        strengths.append("CV thể hiện các kỹ năng bắt buộc: " + ", ".join(matched_required))
    if matched_preferred:
        strengths.append("CV có các kỹ năng ưu tiên: " + ", ".join(matched_preferred))
    if project_section:
        strengths.append("CV có nội dung dự án.")
    if experience_evidence:
        strengths.append("CV có dấu hiệu kinh nghiệm hoặc thực tập.")

    if missing_required:
        improvements.append("Bổ sung bằng chứng thực tế cho kỹ năng bắt buộc còn thiếu: " + ", ".join(missing_required))
    if missing_preferred:
        improvements.append("Cân nhắc bổ sung kỹ năng ưu tiên nếu bạn thực sự có kinh nghiệm: " + ", ".join(missing_preferred))
    if not project_section:
        improvements.append("Bổ sung mục dự án, nêu công nghệ sử dụng và kết quả đạt được.")
    if not education_section:
        improvements.append("Bổ sung mục học vấn hoặc chứng chỉ liên quan.")
    if word_count < 150:
        improvements.append("CV có ít nội dung; hãy bổ sung kinh nghiệm, dự án và thành tựu có thể kiểm chứng.")

    return {
        "overall_score": overall_score,
        "career_level": level,
        "weights": WEIGHTS,
        "breakdown": breakdown,
        "matched_required_skills": matched_required,
        "missing_required_skills": missing_required,
        "matched_preferred_skills": matched_preferred,
        "missing_preferred_skills": missing_preferred,
        "matched_keywords": matched_keywords[:30],
        "strengths": strengths,
        "improvements": improvements,
        "metadata": {
            "word_count": word_count,
            "sections_found": headings_found,
            "required_experience_years": required_years,
            "method": "deterministic_heuristic_v1",
            "limitations": [
                "Điểm là ước lượng theo quy tắc, không phải đánh giá của nhà tuyển dụng.",
                "Cách diễn đạt khác nhau của cùng một kỹ năng có thể chưa được nhận diện.",
                "Số năm kinh nghiệm chỉ được nhận diện khi CV nêu rõ, ví dụ '2 years'.",
            ],
        },
    }
