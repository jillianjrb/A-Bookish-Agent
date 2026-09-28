# A Bookish Agent

An AI agent that recommends your next read from a handful of books you already love, then checks whether a nearby library has it.

> **Status: work in progress.** Early results for book recommendation are promising, but currently improving clarifying questions and a widespread library availability system.

## How it works

1. **Enter 1-5 books** (title required, author optional) in a Streamlit interface.
2. **Verify the books.** Each entry is fuzzy-matched against the [Open Library](https://openlibrary.org/developers/api) API, which tolerates typos and partial titles.
3. **Build a candidate pool.** Subject tags from your books are normalized into genre buckets using an editable rule set (`genre_rules.py`), so "Fantasy - Epic" and "Dark Fantasy" stay distinct. Books are ranked by how many buckets they match.
4. **Clean the blurbs.** Descriptions are fetched, stripped of links and markdown clutter, and truncated for use in prompts.
5. **Ask clarifying questions.** Gemini reads the candidate blurbs and generates 2-3 multiple-choice questions designed to split the pool along real differences (tone, subgenre, setting).

## Planned

- Narrow the candidates to 3 recommendations based on your answers, each with the official blurb and a short explanation that references your books by name
- Check availability at participating libraries through the [LibrariesHacked Catalogues API](https://github.com/LibrariesHacked/catalogues-api)

## Tech stack

Python, Streamlit, Open Library API, Google Gemini API (free tier), `rapidfuzz`, `python-dotenv`

## Known issues

- Open Library requests time out or reset intermittently, which can shrink the candidate pool
- Question generation still needs broader testing
