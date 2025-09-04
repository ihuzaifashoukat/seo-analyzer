try:
    from spellchecker import SpellChecker
except ImportError:  # pragma: no cover - environment dependent
    SpellChecker = None
import re

def perform_spell_check(text_content: str, language: str) -> dict:
    if SpellChecker is None:
        return {"spellCheck": {"status": "skipped_pyspellchecker_not_installed", "misspelled_words_sample": []}}
    try:
        spell = SpellChecker(language=language)
        words_for_spellcheck = re.findall(r'\b[a-zA-Z]+\b', text_content)
        # Reduce size to speed up checks on very long texts
        sample_limit = 5000
        if len(words_for_spellcheck) > sample_limit:
            words_for_spellcheck = words_for_spellcheck[:sample_limit]
        misspelled = spell.unknown([w.lower() for w in words_for_spellcheck])
        misspelled_filtered = [w for w in misspelled if len(w) > 2]
        return {
            "spellCheck": {
                "status": "completed",
                "misspelled_words_sample": misspelled_filtered[:20],
                "misspelled_words_count": len(misspelled_filtered),
            }
        }
    except Exception as e:
        return {"spellCheck": {"status": "error", "error_message": str(e), "misspelled_words_sample": []}}

