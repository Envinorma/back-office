import traceback

from bs4 import BeautifulSoup
from envinorma.io.parse_html import extract_text_elements
from envinorma.models.text_elements import TextElement


def parse_table(element: TextElement) -> TextElement:
    if isinstance(element, str) and '<table>' in element:
        prefix = f"Erreur lors de l'extraction du tableau dans la ligne suivante :\n{element}"
        try:
            elements = extract_text_elements(BeautifulSoup(element, 'html.parser'))
        except Exception:
            raise ValueError(f'{prefix}\n\nErreur complète:\n\n{traceback.format_exc()}')
        if len(elements) == 0:
            raise ValueError(f'{prefix}\nAucun élément n\'a été détecté.')
        if len(elements) > 1:
            element_types = ', '.join([el.__class__.__name__ for el in elements])
            raise ValueError(f'{prefix}\nPlusieurs éléments ont été détectés, dont voici les types :\n{element_types}')
        return elements[0]
    return element
