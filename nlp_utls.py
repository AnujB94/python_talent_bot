import spacy
import re

nlp = spacy.load("en_core_web_sm")

def parse_user_query(text):
    doc = nlp(text.lower())
    
    gender = None
    age_min = None
    age_max = None

    # Extract gender
    if any(token.text in ["female", "girl", "actress"] for token in doc):
        gender = "Female"
    elif any(token.text in ["male", "boy", "actor"] for token in doc):
        gender = "Male"

    # Extract exact age
    age_match = re.search(r"\b(age|aged|about|around|is)\s*(\d{1,2})\b", text, re.IGNORECASE)
    if age_match:
        age = int(age_match.group(2))
        age_min = age - 2
        age_max = age + 2

    # Extract age range
    range_match = re.search(r"(\d{1,2})\s*to\s*(\d{1,2})", text)
    if range_match:
        age_min = int(range_match.group(1))
        age_max = int(range_match.group(2))

    return {
        "gender": gender,
        "age_min": age_min,
        "age_max": age_max
    }