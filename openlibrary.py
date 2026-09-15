"""
Open Library API integration.

- Searches for input books
- verifies that they exist (in OL database)

"""

import requests
from rapidfuzz import fuzz
import re

SEARCH_URL = "https://openlibrary.org/search.json"

# Open Library asks API consumers to identify themselves with a descriptive
# User-Agent. Replace the email with your own contact info.
HEADERS = {"User-Agent": "BookRecommenderAgent/0.1 ([email protected])"}

# Thresholds for fuzzy matching (0-100 scale from rapidfuzz).
# These are starting points -- tune them once you test with real messy input.
CONFIDENT_MATCH_THRESHOLD = 85
AMBIGUOUS_MATCH_THRESHOLD = 60


def search_books(title: str, author: str | None = None, limit: int = 5) -> list[dict]:
    query = title
    params = {
        "q": query,
        "limit": limit,
        "fields": "title,author_name,key,cover_i,isbn,first_publish_year,subject",
    }
    if author:
        params["q"] = f"{title} author:{author}"

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("docs", [])
        except requests.RequestException as e:
            if attempt < max_retries:
                print(f"Attempt {attempt} failed for '{title}': {e}. Retrying...")
                continue
            else:
                print(f"Open Library request failed after {max_retries} attempts: {e}")
                return []

WORKS_URL = "https://openlibrary.org/works/{olid}.json"


def fetch_description(olid: str) -> str | None:
    """
    Fetch a work's description from its work record. This is a SEPARATE
    API call from search -- descriptions are not available via search.json.
    """
    if not olid:
        return None

    url = WORKS_URL.format(olid=olid)
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        description = data.get("description")
        # description can be a plain string OR a dict like {"type": "...", "value": "..."}
        if isinstance(description, dict):
            description = description.get("value")
        return sanitize_description(description)
    except requests.RequestException as e:
        print(f"Failed to fetch description for {olid}: {e}")
        return None

def sanitize_description(text: str | None) -> str | None:
    """
    Description data is stripped of unnecessary characters (links, md formatting, decorative, etc.)
    that we do not want prompted to LLM.
    """
    if not text:
        return text

    # Remove reference-style link definition lines, e.g. "[1]: https://openlibrary.org/..."
    text = re.sub(r'^\s*\[\d+\]:\s*\S+.*$', '', text, flags=re.MULTILINE)

    # Collapse reference-style links [text][n] -> text
    text = re.sub(r'\[([^\]]+)\]\[\d+\]', r'\1', text)

    # Collapse inline markdown links [text](url) -> text
    text = re.sub(r'\[([^\]]+)\]\(https?://[^\)]+\)', r'\1', text)

    # Remove any remaining bare URLs not caught above
    text = re.sub(r'https?://\S+', '', text)

    # Remove horizontal rule lines (e.g. "----------")
    text = re.sub(r'^-{3,}\s*$', '', text, flags=re.MULTILINE)

    # Strip markdown bold/italic markers, keep the text inside
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)

    # Strip markdown headers (e.g. "# Title" or "## Subtitle")
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)

    # Remove common footer/attribution lines
    footer_patterns = [
        r'^\s*\(source\)\s*$',
        r'^\s*\(from the paperback.*?\)\s*$',
        r'^\s*from the paperback.*$',
        r'^\s*this (work|book) is in the following (series|collections?):?\s*$',
        r'^\s*the following ebook links were found elsewhere online:?\s*$',
        r'^\s*see also the graphic novel adaptation.*$',
        r'^\s*preceded by:.*$',
        r'^\s*followed by:.*$',
    ]
    for pattern in footer_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)

    # Remove bullet-point series/collection list lines (e.g. "- Forgotten Realms")
    text = re.sub(r'^\s*-\s+.+$', '', text, flags=re.MULTILINE)

    # Clean up leftover blank lines and extra whitespace from the removals
    text = re.sub(r'\n{2,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()

    return text

def truncate_blurb(text: str | None, max_non_space_chars: int = 500) -> str | None:
    """
    Truncate text after the Nth non-space character (default 500)
    """
    if not text:
        return text

    non_space_count = 0
    cutoff_index = len(text)  # default: no truncation needed

    for i, char in enumerate(text):
        if not char.isspace():
            non_space_count += 1
        if non_space_count > max_non_space_chars:
            cutoff_index = i
            break

    truncated = text[:cutoff_index]

    if cutoff_index < len(text):
        truncated = truncated.rstrip() + "..."

    return truncated

def _extract_book_info(doc: dict) -> dict:
    """Pull the fields we care about from a raw Open Library search result."""
    cover_id = doc.get("cover_i")
    cover_url = (
        f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg" if cover_id else None
    )
    isbn_list = doc.get("isbn", [])

    return {
        "title": doc.get("title", "Unknown title"),
        "author": ", ".join(doc.get("author_name", ["Unknown author"])),
        "olid": doc.get("key", "").replace("/works/", ""),
        "isbn": isbn_list[0] if isbn_list else None,
        "isbn_list": isbn_list,  # keep the full list; you may need to try
                                  # multiple ISBNs later when checking
                                  # library availability
        "cover_url": cover_url,
        "first_publish_year": doc.get("first_publish_year"),
        "subjects": doc.get("subject", [])[:10],  # useful later for Day 2
        "description": None,  # not available from search.json --
                               # fetch separately via fetch_description(olid)
                               # only when you actually need the blurb text
    }


def verify_book(title: str, author: str | None = None) -> dict:
    """
    Verify that a user-entered title/author corresponds to a real book.

    Returns a dict with one of three statuses:
      - "found": a single confident match
      - "ambiguous": multiple plausible matches, need user disambiguation
      - "not_found": no good match
    """
    results = search_books(title, author)

    if not results:
        return {"status": "not_found", "query": title}

    # Score each result against the user's input title using fuzzy matching
    scored = []
    for doc in results:
        result_title = doc.get("title", "")
        score = fuzz.ratio(title.lower(), result_title.lower())
        scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_doc = scored[0]

    if best_score >= CONFIDENT_MATCH_THRESHOLD:
        return {"status": "found", "book": _extract_book_info(best_doc)}

    elif best_score >= AMBIGUOUS_MATCH_THRESHOLD:
        # Return top few candidates for the user to disambiguate
        candidates = [_extract_book_info(doc) for score, doc in scored[:3]]
        return {"status": "ambiguous", "query": title, "candidates": candidates}

    else:
        return {"status": "not_found", "query": title}