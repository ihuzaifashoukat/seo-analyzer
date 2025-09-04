import re

# Basic list of English stopwords (can be expanded or made configurable)
STOPWORDS = set([
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "if", "in", 
    "into", "is", "it", "no", "not", "of", "on", "or", "such", "that", "the", 
    "their", "then", "there", "these", "they", "this", "to", "was", "will", "with",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", 
    "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", 
    "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", 
    "theirs", "themselves", "what", "which", "who", "whom", "this", "that", 
    "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", 
    "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", 
    "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", 
    "at", "by", "for", "with", "about", "against", "between", "into", "through", 
    "during", "before", "after", "above", "below", "to", "from", "up", "down", 
    "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", 
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", 
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", 
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", 
    "don", "should", "now"
])

def get_words_from_text(text: str, remove_stopwords=True, min_word_length=3) -> list:
    """Tokenize text into words and optionally remove stopwords/short words."""
    text = text.lower()
    words = re.findall(r'\b[a-z0-9]+\b', text)
    if remove_stopwords:
        words = [word for word in words if word not in STOPWORDS and len(word) >= min_word_length]
    else:
        words = [word for word in words if len(word) >= min_word_length]
    return words

def count_syllables(word: str) -> int:
    word = word.lower()
    if not word:
        return 0
    word = re.sub(r'[^a-z]', '', word)
    if len(word) <= 3:
        return 1
    if word.endswith("e") and not word.endswith("le") and len(word) > 1:
        word = word[:-1]
    vowels = "aeiouy"
    syllable_count = 0
    prev_char_was_vowel = False
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_char_was_vowel:
            syllable_count += 1
        prev_char_was_vowel = is_vowel
    return max(1, syllable_count)

