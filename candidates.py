"""
Generates books that are candidates for recommendation, based on the subjects of the
user's verified input books. The output is a ranked list of candidates.
"""

from collections import Counter
import re
import requests
from genre_rules import canonicalize_subject
import time

from openlibrary import HEADERS  # reuse the same User-Agent header
from openlibrary import fetch_description, truncate_blurb

SUBJECTS_URL = "https://openlibrary.org/subjects/{slug}.json"

TOP_N_SUBJECTS = 5
RESULTS_PER_SUBJECT = 20  # how many works to pull per subject query

## Step 1:
def extract_top_subjects(verified_books: list[dict], top_n: int = TOP_N_SUBJECTS) -> list[str]:
    """
    Given the verified books (user's input books), extract the top_n most frequent canonicalized subject buckets.
    Canonicalized subjects are put into into a genre buckets (via genre_rules.py)
    Returns a list of the top_n canonicalized subject buckets, sorted by frequency descending.

    """
    bucket_counter = Counter()

    for book in verified_books:
        subjects = book.get("subjects", [])
        buckets_in_this_book = set()
        for subject in subjects:
            bucket = canonicalize_subject(subject)
            if bucket:
                buckets_in_this_book.add(bucket)
        for bucket in buckets_in_this_book:
            bucket_counter[bucket] += 1

    most_common = bucket_counter.most_common(top_n)
    return [bucket for bucket, count in most_common]

## STEP 2
def slugify_subject(subject: str) -> str:
    """
    A slug is a lowercase, underscore-separated string with punctuation stripped.
    This is the format the Open Library Subjects API expects.
    """
    s = subject.lower().strip()
    s = re.sub(r"[^\w\s]", "", s)  # strip punctuation (commas, slashes, etc.)
    s = re.sub(r"\s+", "_", s)     # collapse whitespace to single underscores
    return s

## STEP 3
def query_subject(slug: str, limit: int = RESULTS_PER_SUBJECT) -> list[dict]:
    """
    Query the Open Library Subjects API for a given subject slug, returning a list of works.
    Each work is a dict with keys like 'key', 'title', 'authors', etc
    """
    url = SUBJECTS_URL.format(slug=slug)
    params = {"limit": limit}
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("works", [])
    except requests.RequestException as e:
        print(f"Subject query failed for '{slug}': {e}")
        return []


def build_candidate_pool(verified_books: list[dict], exclude_olids: set[str] = None) -> list[dict]:
    """
    Using top subjects and multi-subject match ranking, candidate pool is generated.

    'exclude_olids' is a set of OLIDs to skip  -> prevents user's input books from being candidates

    Returns a list of dicts sorted by match_count descending, each:
      {"olid", "title", "author", "cover_url", "match_count"}
    where match_count = number of queried subjects this book appeared under.
    """
    exclude_olids = exclude_olids or set()

    top_subjects = extract_top_subjects(verified_books)
    slugs = [slugify_subject(s) for s in top_subjects]

    match_counts = Counter()   # olid -> number of subject queries it appeared in
    candidate_info = {}        # olid -> extracted info (title, author, etc.)

    for slug in slugs:
        works = query_subject(slug)
        time.sleep(1)
        seen_in_this_query = set()  # avoid double-counting if API returns dupes within one query
        for work in works:
            olid = work.get("key", "").replace("/works/", "")
            if not olid or olid in seen_in_this_query:
                continue
            seen_in_this_query.add(olid)

            if olid in exclude_olids:
                continue

            match_counts[olid] += 1

            if olid not in candidate_info:
                cover_id = work.get("cover_id")
                cover_url = (
                    f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                    if cover_id else None
                )
                candidate_info[olid] = {
                    "olid": olid,
                    "title": work.get("title", "Unknown title"),
                    "author": ", ".join(
                        a.get("name", "") for a in work.get("authors", [])
                    ) or "Unknown author",
                    "cover_url": cover_url,
                }

    candidates = []
    for olid, info in candidate_info.items():
        info["match_count"] = match_counts[olid]
        candidates.append(info)

    candidates.sort(key=lambda c: c["match_count"], reverse=True)
    return candidates

def enrich_candidates_with_blurbs(candidates: list[dict], top_n: int = 15) -> list[dict]:
    """
    top_n candidates from build_candidate_pool:
    - fetch blurb
    - truncate blurb
    - attach blurb to candidate dict
    - drop candidates with no blurb
    """
    top_candidates = candidates[:top_n]
    enriched = []

    for candidate in top_candidates:
        blurb = fetch_description(candidate["olid"])
        time.sleep(1)

        # Drop candidates without blurbs
        if blurb is None:
            print(f"Dropping candidate '{candidate['title']}' -- no blurb available.")
            continue

        # Truncate the blurb to a given amount of characters
        candidate["blurb"] = truncate_blurb(blurb, max_non_space_chars=500)
        enriched.append(candidate)

    return enriched