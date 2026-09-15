"""
Generate questions for narrowing down the list of candidates
"Agentic" component

"""

import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3.6-flash"

"""
Question output: list of questions, each with question text and 2-3 answer options.
Must include relevant answers.
"""
QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_text": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "candidate_titles": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["label", "candidate_titles"],
                        },
                    },
                },
                "required": ["question_text", "options"],
            },
        }
    },
    "required": ["questions"],
}


def build_prompt(input_books: list[dict], candidates: list[dict]) -> str:
    """Build the prompt text describing the user's books and candidates."""
    input_lines = "\n".join(
        f"- {b['title']} by {b['author']}" for b in input_books
    )
    candidate_lines = "\n\n".join(
        f"Title: {c['title']}\nAuthor: {c['author']}\nBlurb: {c['blurb']}"
        for c in candidates
    )

    return f"""The user enjoyed these books:
{input_lines}

Here are {len(candidates)} candidate books being considered as recommendations for them:

{candidate_lines}

Generate 2-3 multiple-choice clarifying questions that will help narrow down
which candidates best fit the user's taste. Each question must have 2-3
answer options. Each answer option must correspond to a REAL, meaningful
subset of the candidate titles listed above (use the exact titles as given)
-- do not invent a question where nearly all candidates fall under one
option. Base the questions on genuine differences you notice in the blurbs
(tone, setting, subgenre, themes, etc.), not superficial details."""


def generate_questions(input_books: list[dict], candidates: list[dict]) -> dict:
    """
    Call Gemini for clarifying questions
    Returns the JSON dict matching QUESTION_SCHEMA, or raises if
    the response can't be parsed.
    """
    prompt = build_prompt(input_books, candidates)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QUESTION_SCHEMA,
        ),
    )

    return json.loads(response.text)