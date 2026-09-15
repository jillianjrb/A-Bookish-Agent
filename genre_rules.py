"""
Genre canonicalization rules.  Maps Open Libary subject strings to simplified genre buckets.

Edit GENRE_RULES and SUBJECT_BLOCKLIST here to tune which genres/subjects are kept and omitted.
"""

import re

# Ordered list of (phrase, canonical_bucket) rules, checked top to bottom.
# The FIRST matching phrase wins -- so more specific multi-word phrases
# must appear before their broader/generic counterparts. Add new rules
# here as you notice subjects being bucketed too generically.
GENRE_RULES = [
    # --- fantasy subgenres (specific first) ---
    ("dark fantasy", "dark_fantasy"),
    ("grimdark", "dark_fantasy"),
    ("fantasy romance", "fantasy_romance"),
    ("romantic fantasy", "fantasy_romance"),
    ("urban fantasy", "urban_fantasy"),
    ("epic fantasy", "epic_fantasy"),
    ("high fantasy", "epic_fantasy"),
    ("sword and sorcery", "sword_and_sorcery"),
    ("fantasy fiction", "fantasy"),
    ("fantasy", "fantasy"),  # generic fallback -- must stay last in this group

    # --- science fiction subgenres ---
    ("space opera", "space_opera"),
    ("science fiction romance", "scifi_romance"),
    ("hard science fiction", "hard_scifi"),
    ("science fiction", "science_fiction"),
    ("science-fiction", "science_fiction"),
    ("sci-fi", "science_fiction"),

    # --- romance subgenres ---
    ("erotica", "erotica"),
    ("romance", "romance"),  # generic fallback

    # --- mystery / thriller ---
    ("cozy mystery", "cozy_mystery"),
    ("psychological thriller", "psychological_thriller"),
    ("mystery", "mystery"),
    ("thriller", "thriller"),

    # add more rules here as needed
]

# Subjects that should NEVER be treated as genre-level signal, even if they
# slip past the comma/structure heuristic. Add terms here as you spot junk
# candidates slipping through (character names, objects, animals, etc.)
SUBJECT_BLOCKLIST = {
    "fiction", "general", "juvenile fiction", "american literature",
}


def _normalize_for_matching(subject: str) -> str:
    """Lowercase and strip punctuation for phrase matching."""
    s = subject.lower()
    s = re.sub(r"[^\w\s]", " ", s)  # punctuation -> space (keeps word boundaries)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonicalize_subject(subject: str) -> str | None:
    """
    OL "subjects" are grouped together as genres to minimize subject fragmentation.

    Matching is word-set based (order-independent): a rule matches if
    ALL of its words appear somewhere in the subject, regardless of order.
    This handles variants like "Fantasy - Epic" vs "Epic Fantasy".

    Returns None if the subject doesn't match any rule and isn't
    considered genre-level signal (e.g. "thrushes", "Arkenstone").
    """
    normalized = _normalize_for_matching(subject)
    subject_words = set(normalized.split())

    if normalized in SUBJECT_BLOCKLIST:
        return None

    for phrase, bucket in GENRE_RULES:
        phrase_words = set(phrase.split())
        if phrase_words.issubset(subject_words):
            return bucket

    return None