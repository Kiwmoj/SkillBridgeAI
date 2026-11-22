"""Match the skills a learner types in their own words to official O*NET descriptors.

Matching is deliberately transparent: a skill counts when it names a descriptor (or most of its words),
or when it is a common everyday phrase mapped to the descriptors that cover it (for example
"communication" covers Speaking, Writing and Active Listening). Every match records the phrase it came from.
"""
import re

STOP_WORDS = frozenset({"and", "the", "for", "with", "skills", "skill", "good", "basic", "strong", "some", "using"})

# Everyday wording -> official O*NET descriptor names (skills, knowledge, abilities and work styles).
SYNONYMS: dict[str, tuple[str, ...]] = {
    "communication": ("Speaking", "Writing", "Active Listening", "Oral Expression", "Written Expression"),
    "communicating": ("Speaking", "Writing", "Active Listening", "Oral Expression", "Written Expression"),
    "public speaking": ("Speaking", "Oral Expression"),
    "presentation": ("Speaking", "Oral Expression"),
    "presenting": ("Speaking", "Oral Expression"),
    "speaking": ("Speaking", "Oral Expression"),
    "writing": ("Writing", "Written Expression"),
    "listening": ("Active Listening", "Oral Comprehension"),
    "reading": ("Reading Comprehension", "Written Comprehension"),
    "teamwork": ("Cooperation", "Coordination", "Social Perceptiveness", "Social Orientation"),
    "team player": ("Cooperation", "Coordination", "Social Orientation"),
    "collaboration": ("Cooperation", "Coordination", "Social Orientation"),
    "collaborating": ("Cooperation", "Coordination", "Social Orientation"),
    "leadership": ("Leadership", "Management of Personnel Resources", "Coordination"),
    "leading": ("Leadership", "Management of Personnel Resources", "Coordination"),
    "management": ("Management of Personnel Resources", "Administration and Management", "Coordination"),
    "project management": ("Coordination", "Time Management", "Administration and Management"),
    "problem solving": ("Complex Problem Solving", "Critical Thinking", "Problem Sensitivity",
                        "Judgment and Decision Making"),
    "analytical": ("Analytical Thinking", "Critical Thinking", "Deductive Reasoning", "Inductive Reasoning"),
    "analysis": ("Analytical Thinking", "Critical Thinking", "Systems Analysis"),
    "decision making": ("Judgment and Decision Making",),
    "math": ("Mathematics", "Mathematical Reasoning", "Number Facility"),
    "maths": ("Mathematics", "Mathematical Reasoning", "Number Facility"),
    "algebra": ("Mathematics", "Mathematical Reasoning"),
    "calculus": ("Mathematics", "Mathematical Reasoning"),
    "statistics": ("Mathematics", "Mathematical Reasoning"),
    "computer": ("Computers and Electronics",),
    "computers": ("Computers and Electronics",),
    "technology": ("Computers and Electronics", "Technology Design"),
    "software": ("Computers and Electronics", "Programming"),
    "programming": ("Programming", "Computers and Electronics"),
    "coding": ("Programming", "Computers and Electronics"),
    "python": ("Programming", "Computers and Electronics"),
    "java": ("Programming", "Computers and Electronics"),
    "javascript": ("Programming", "Computers and Electronics"),
    "sql": ("Programming", "Computers and Electronics"),
    "excel": ("Computers and Electronics", "Administrative"),
    "time management": ("Time Management",),
    "organization": ("Time Management", "Information Ordering", "Administrative"),
    "organisation": ("Time Management", "Information Ordering", "Administrative"),
    "planning": ("Time Management", "Coordination", "Information Ordering"),
    "attention to detail": ("Attention to Detail", "Perceptual Speed", "Problem Sensitivity", "Information Ordering"),
    "detail oriented": ("Attention to Detail", "Perceptual Speed", "Information Ordering"),
    "creativity": ("Originality", "Fluency of Ideas", "Innovation", "Design"),
    "creative": ("Originality", "Fluency of Ideas", "Innovation", "Design"),
    "innovation": ("Innovation", "Originality"),
    "research": ("Science", "Reading Comprehension", "Active Learning", "Analytical Thinking"),
    "learning": ("Active Learning", "Learning Strategies"),
    "quick learner": ("Active Learning", "Learning Strategies"),
    "customer service": ("Customer and Personal Service", "Service Orientation"),
    "sales": ("Sales and Marketing", "Persuasion", "Customer and Personal Service"),
    "marketing": ("Sales and Marketing", "Communications and Media", "Persuasion"),
    "social media": ("Communications and Media", "Sales and Marketing"),
    "empathy": ("Social Perceptiveness", "Concern for Others", "Service Orientation"),
    "compassion": ("Social Perceptiveness", "Concern for Others", "Service Orientation"),
    "caring": ("Concern for Others", "Service Orientation", "Social Perceptiveness"),
    "patient care": ("Medicine and Dentistry", "Service Orientation", "Concern for Others",
                     "Customer and Personal Service"),
    "hospital": ("Medicine and Dentistry", "Customer and Personal Service", "Service Orientation"),
    "clinical": ("Medicine and Dentistry", "Biology"),
    "healthcare": ("Medicine and Dentistry", "Service Orientation"),
    "first aid": ("Medicine and Dentistry",),
    "teaching": ("Instructing", "Education and Training"),
    "tutoring": ("Instructing", "Education and Training"),
    "mentoring": ("Instructing", "Education and Training", "Social Perceptiveness"),
    "training": ("Instructing", "Education and Training"),
    "adaptability": ("Adaptability/Flexibility", "Tolerance for Ambiguity", "Initiative"),
    "flexibility": ("Adaptability/Flexibility", "Tolerance for Ambiguity"),
    "reliable": ("Dependability", "Integrity"),
    "dependable": ("Dependability", "Integrity"),
    "responsible": ("Dependability", "Integrity"),
    "initiative": ("Initiative", "Achievement Orientation"),
    "self motivated": ("Initiative", "Achievement Orientation", "Persistence"),
    "resilience": ("Stress Tolerance", "Persistence"),
    "stress": ("Stress Tolerance",),
    "negotiation": ("Negotiation", "Persuasion"),
    "persuasion": ("Persuasion", "Negotiation"),
    "accounting": ("Economics and Accounting", "Management of Financial Resources", "Mathematics"),
    "finance": ("Economics and Accounting", "Management of Financial Resources", "Mathematics"),
    "budgeting": ("Management of Financial Resources", "Economics and Accounting"),
    "design": ("Design", "Originality", "Visualization", "Fine Arts"),
    "graphic design": ("Design", "Visualization", "Fine Arts", "Originality"),
    "drawing": ("Fine Arts", "Visualization", "Design"),
    "art": ("Fine Arts", "Design", "Originality"),
    "engineering": ("Engineering and Technology", "Mechanical", "Design"),
    "law": ("Law and Government",),
    "legal": ("Law and Government",),
    "compliance": ("Law and Government",),
    "spanish": ("Foreign Language",),
    "french": ("Foreign Language",),
    "bilingual": ("Foreign Language",),
    "translation": ("Foreign Language",),
    "biology": ("Biology",),
    "chemistry": ("Chemistry",),
    "physics": ("Physics",),
    "science": ("Science", "Biology", "Chemistry", "Physics"),
    "repair": ("Repairing", "Equipment Maintenance", "Mechanical"),
    "repairing": ("Repairing", "Equipment Maintenance", "Mechanical"),
    "mechanic": ("Mechanical", "Repairing", "Equipment Maintenance"),
    "maintenance": ("Equipment Maintenance", "Repairing"),
    "driving": ("Operation and Control", "Transportation"),
    "typing": ("Administrative", "Computers and Electronics"),
    "data entry": ("Administrative", "Computers and Electronics", "Clerical"),
    "administration": ("Administrative", "Administration and Management"),
    "office": ("Administrative", "Clerical"),
    "cooking": ("Food Production",),
    "construction": ("Building and Construction",),
}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9+#/ ]+", " ", text.lower()).strip()


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) - len(suffix) >= 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _tokens(text: str) -> set[str]:
    return {_stem(word) for word in re.findall(r"[a-z0-9+#]+", text.lower()) if len(word) > 2 and word not in STOP_WORDS}


def _contains(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def match_descriptors(phrase: str, names: dict[str, str]) -> set[str]:
    """Return the keys (casefolded descriptor names) that the phrase refers to. ``names`` maps key -> display name."""
    text = normalize(phrase)
    if not text:
        return set()
    wanted = _tokens(text)
    hits: set[str] = set()
    for key, name in names.items():
        candidate = normalize(name)
        name_tokens = _tokens(name)
        if candidate == text or _contains(text, candidate):
            hits.add(key)
        elif len(text) >= 5 and _contains(candidate, text):
            hits.add(key)
        elif name_tokens and wanted and (name_tokens <= wanted or (wanted <= name_tokens and len(wanted) >= 1
                                                                   and max(map(len, wanted)) >= 5)):
            hits.add(key)
    for synonym, targets in SYNONYMS.items():
        if _contains(text, synonym):
            hits.update(target.casefold() for target in targets if target.casefold() in names)
    return hits


def match_tools(phrase: str, tools: list[str]) -> list[str]:
    text = normalize(phrase)
    if len(text) < 3:
        return []
    return [tool for tool in tools if _contains(normalize(tool), text) or _contains(text, normalize(tool))]
