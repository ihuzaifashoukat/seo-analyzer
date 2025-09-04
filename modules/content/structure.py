import re
from bs4 import BeautifulSoup, Comment

CTA_PHRASES = [
    'buy now','shop now','get started','try now','sign up','contact us','book now','download','discover','find out','see how','start now','join now','request a quote','subscribe','learn more','read more'
]

def analyze_content_structure(html_soup: BeautifulSoup, text: str) -> dict:
    paragraphs = html_soup.find_all('p')
    num_paragraphs = len(paragraphs)
    para_lengths = [len(p.get_text(strip=True).split()) for p in paragraphs]
    avg_para_len = round(sum(para_lengths) / num_paragraphs, 2) if num_paragraphs else 0

    bullets = len(html_soup.find_all('ul'))
    numbered = len(html_soup.find_all('ol'))

    # Passive voice heuristic: "was|were|be|been" + past participle ending with -ed (very rough)
    passive_matches = re.findall(r"\b(was|were|be|been|being)\b\s+\b(\w+ed)\b", text.lower())
    passive_ratio = round(len(passive_matches) / max(1, len(text.split())), 3)

    cta_present = any(phrase in text.lower() for phrase in CTA_PHRASES)

    return {
        'paragraphCount': num_paragraphs,
        'avgParagraphWordCount': avg_para_len,
        'bulletListCount': bullets,
        'numberedListCount': numbered,
        'passiveVoiceRatio': passive_ratio,
        'hasCTAPhrases': cta_present,
    }

