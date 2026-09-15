'''
Test script for generation of clarifying questions
'''

from test_data import SAMPLE_CANDIDATES
from questions import generate_questions

# Sample input books for testing
input_books = [
    {"title": "The Hobbit", "author": "J.R.R. Tolkien"},
    {"title": "Dune", "author": "Frank Herbert"},
    {"title": "The Name of the Wind", "author": "Patrick Rothfuss"},
    {"title": "The Lies of Locke Lamora", "author": "Scott Lynch"},
]

result = generate_questions(input_books, SAMPLE_CANDIDATES)

for i, q in enumerate(result["questions"], 1):
    print(f"\nQ{i}: {q['question_text']}")
    for opt in q["options"]:
        print(f"  - {opt['label']}: {opt['candidate_titles']}")