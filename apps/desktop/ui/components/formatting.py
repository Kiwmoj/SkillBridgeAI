from typing import Any

# Sidebar labels for every signed-in user, in display order; administrators get one extra page.
BASE_NAV_ITEMS: list[str] = [
    "Dashboard",
    "My Profile",
    "Career Explorer",
    "Career Reality Check",
    "Skill Gap Analyzer",
    "Learning Roadmap",
    "Portfolio Reviewer",
    "Project Generator",
    "Opportunities & Colleges",
    "Progress Analytics",
    "Community",
    "Settings",
]
AI_NOTICE = "AI requests use the configured provider. Only share material you are allowed to send; remove private information."


def generated_text(answer: str, sources: list[dict[str, Any]], generated: bool = True) -> str:
    header = "AI-generated guidance" if generated else "Compiled from official sources (not AI-generated)"
    lines = [header, "", answer, "", "Retrieved references:"]
    for source in sources:
        label = "Reviewed community contribution" if source["source_type"] == "community" else source["source_type"]
        lines.append(f"[{source['id']}] {source['title']} ({label})\n"
                     f"{source.get('reference') or ''}\n{source.get('url') or ''}\n{source['text']}")
    if not sources:
        lines.append("No relevant references were retrieved.")
    return "\n".join(lines)
