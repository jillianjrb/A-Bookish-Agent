from openlibrary import verify_book
from candidates import build_candidate_pool, extract_top_subjects, slugify_subject
from candidates import build_candidate_pool, enrich_candidates_with_blurbs
import time
from test_data import SAMPLE_CANDIDATES

# manually verify a couple of test books first
book_queries = [
    ("The Hobbit", "Tolkien"),
    ("Dune", "Frank Herbert"),
    ("The Name of the Wind", "Patrick Rothfuss"),
    ("The Lies of Locke Lamora", "Scott Lynch"),
]

results = []
for title, author in book_queries:
    results.append(verify_book(title, author))
    time.sleep(1)

found_books = [r["book"] for r in results if r["status"] == "found"]
if not found_books:
    print("No verified books found; cannot build candidate pool.")
    exit(1)
'''for book in found_books:
    print(book["title"], "-", book["author"], book["subjects"], book["description"])'''
# Access the first book directly using index 0
first_book = found_books[0]
print(first_book["title"], "-", first_book["author"], first_book["subjects"], first_book["description"])

# --- Sanity check: per-book subject canonicalization ---
from genre_rules import canonicalize_subject

print("=== Per-book subject -> bucket mapping ===")
for book in found_books:
    print(f"\n{book['title']} - {book['author']}")
    for subject in book.get("subjects", []):
        bucket = canonicalize_subject(subject)
        print(f"  '{subject}' -> {bucket}")

# --- Sanity check: aggregated top subjects ---
print("\n=== Top 5 canonical buckets across all input books ===")
top_subjects = extract_top_subjects(found_books)
print(top_subjects)

pool = build_candidate_pool(found_books)
if not pool:
    print("No candidates found; try different input books.")
    exit(1)

enriched = enrich_candidates_with_blurbs(pool, top_n=15)

print("\n=== Top candidates with blurbs ===")
for c in enriched:
    print(f"\n{c['match_count']}  {c['title']} - {c['author']}")
    print(f"  {c['blurb']}")