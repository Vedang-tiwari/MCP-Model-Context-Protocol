"""Strict Role Matching and Semantic Verification Module.

Enforces target role keyword matching across job titles, tags, and descriptions
to ensure discovery sweeps only ingest listings matching configured user targets.
"""
import re
from typing import List, Optional, Set, Dict, Any

ROLE_ALIASES: Dict[str, List[str]] = {
    "swe": ["software engineer", "swe", "sde", "software development engineer", "software developer"],
    "sde": ["software development engineer", "sde", "software engineer", "swe"],
    "fde": ["forward deployed engineer", "forward deployment engineer", "fde", "forward deployed"],
    "ai": ["ai", "artificial intelligence", "gen ai", "generative ai", "genai", "llm", "large language model"],
    "ml": ["ml", "machine learning", "deep learning"],
    "devops": ["devops", "site reliability", "sre", "platform engineer", "cloud engineer", "infrastructure engineer"],
    "frontend": ["frontend", "front end", "ui engineer", "web engineer", "react developer"],
    "backend": ["backend", "back end", "server engineer", "api engineer"],
    "fullstack": ["full stack", "fullstack", "end to end"],
    "data": ["data engineer", "big data engineer", "analytics engineer", "data platform"],
    "blockchain": ["blockchain", "web3", "solidity", "smart contract", "crypto"],
}

# Precompute bidirectional alias index for O(1) lookups
BIDIRECTIONAL_ALIASES: Dict[str, Set[str]] = {}
for _k, _aliases in ROLE_ALIASES.items():
    _group = set([_k] + _aliases)
    for _item in _group:
        BIDIRECTIONAL_ALIASES.setdefault(_item, set()).update(_group)

EQUIVALENCES: Dict[str, Set[str]] = {
    "engineer": {"engineer", "developer", "programmer", "architect", "specialist", "dev"},
    "developer": {"engineer", "developer", "programmer", "architect", "specialist", "dev"},
    "programmer": {"engineer", "developer", "programmer", "architect", "dev"},
    "dev": {"engineer", "developer", "programmer", "architect", "dev"},
    "gen": {"gen", "generative", "genai"},
    "ai": {"ai", "artificial intelligence", "genai", "llm"},
    "ml": {"ml", "machine learning", "deep learning"},
    "fullstack": {"fullstack", "full stack"},
    "frontend": {"frontend", "front end", "client"},
    "backend": {"backend", "back end", "server"},
}

STOP_WORDS = {"and", "or", "the", "of", "for", "in", "at", "to", "a", "an", "with", "level", "senior", "lead", "staff", "junior", "principal"}


def matches_target_roles(
    title: str,
    target_roles: List[str],
    tags: Optional[List[str]] = None,
    description: Optional[str] = None
) -> bool:
    """
    Checks if a job title and metadata match any of the active target role keywords.
    When target_roles is provided, strict matching is enforced:
    listing must align with at least one target keyword.
    """
    if not target_roles:
        return True

    title_lower = title.lower()
    clean_title = re.sub(r'[^a-z0-9+#]', ' ', title_lower)
    title_words = set(clean_title.split())
    tag_set = set(t.lower() for t in (tags or []))

    for target in target_roles:
        target_clean = target.lower().strip()
        if not target_clean:
            continue

        # 1. Exact phrase match in title or tags
        if target_clean in title_lower or target_clean in tag_set:
            return True

        # 2. Direct bidirectional alias match
        if target_clean in BIDIRECTIONAL_ALIASES:
            for alias in BIDIRECTIONAL_ALIASES[target_clean]:
                if alias in title_words or alias in title_lower or alias in tag_set:
                    return True

        # 3. Token-based matching: all non-stop tokens of target keyword must match
        raw_tokens = [tok for tok in re.split(r'[^a-z0-9+#]', target_clean) if tok]
        significant_tokens = [tok for tok in raw_tokens if tok not in STOP_WORDS]
        if not significant_tokens:
            significant_tokens = raw_tokens

        if not significant_tokens:
            continue

        matched_all = True
        for tok in significant_tokens:
            tok_matched = False

            # Direct word boundary or exact token in words/tags
            if tok in title_words or tok in tag_set:
                tok_matched = True
            elif tok in EQUIVALENCES:
                if any(eq in title_words or eq in tag_set for eq in EQUIVALENCES[tok]):
                    tok_matched = True
            elif tok in BIDIRECTIONAL_ALIASES:
                if any(alias in title_words or alias in title_lower or alias in tag_set for alias in BIDIRECTIONAL_ALIASES[tok]):
                    tok_matched = True
            elif len(tok) >= 4 and any(tok in w for w in title_words):
                tok_matched = True

            if not tok_matched:
                matched_all = False
                break

        if matched_all:
            return True

    return False
