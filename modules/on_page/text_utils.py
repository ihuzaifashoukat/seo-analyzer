from bs4 import BeautifulSoup, Comment

def extract_visible_text(soup: BeautifulSoup) -> str:
    text_soup = BeautifulSoup(str(soup), 'html.parser')
    for element in text_soup(["script", "style", "nav", "footer", "aside", "header", "noscript"]):
        element.decompose()
    for comment in text_soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    return text_soup.get_text(separator=" ", strip=True)

