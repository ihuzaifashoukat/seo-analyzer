import re
from .text_utils import count_syllables

def calculate_flesch_reading_ease(text_content: str) -> dict:
    words = re.findall(r"\b[\w'-]+\b", text_content)
    sentences = re.split(r'[.!?]+', text_content)
    words = [word for word in words if word]
    sentences = [sentence for sentence in sentences if sentence.strip()]
    num_words = len(words)
    num_sentences = len(sentences)
    if num_words < 100 or num_sentences < 3:
        return {
            "flesch_reading_ease_score": None,
            "flesch_reading_interpretation": "Not enough content (at least 100 words and 3 sentences recommended).",
        }
    num_syllables = sum(count_syllables(word) for word in words)
    try:
        asl = (num_words / num_sentences)
        asw = (num_syllables / num_words)
        score = round(206.835 - 1.015 * asl - 84.6 * asw, 2)
    except ZeroDivisionError:
        return {"flesch_reading_ease_score": None, "flesch_reading_interpretation": "Calculation error."}

    interpretation = "N/A"
    if score >= 90:
        interpretation = "Very easy to read."
    elif score >= 70:
        interpretation = "Easy to read."
    elif score >= 60:
        interpretation = "Plain English."
    elif score >= 50:
        interpretation = "Fairly difficult to read."
    elif score >= 30:
        interpretation = "Difficult to read."
    else:
        interpretation = "Very difficult to read."
    # Flesch-Kincaid Grade Level
    fk_grade = round(0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59, 2)
    return {
        "flesch_reading_ease_score": score,
        "flesch_reading_interpretation": interpretation,
        "flesch_kincaid_grade": fk_grade,
        "avg_sentence_length": round(asl, 2),
        "avg_syllables_per_word": round(asw, 2),
    }
