import hashlib
import re
from typing import Any
from xml.etree.ElementTree import Element

document_pattern = re.compile(
    r"javascript:loadResult\(\'(.*\.(pdf|PDF))\'\,\'(.*\.(pdf|PDF))\'\)"
)

html_pattern = re.compile(r"loadResult\(\'(.*\.(pdf|PDF))\'\,\'(.*\.(pdf|PDF))\'\)")


def fingerprint(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def extract_pdf_link(el: Element | Any) -> str:
    if el.attrib.get("name") == "myurl" and el.text is not None and el.text != "#":
        text = el.text.replace("\n", "")
        text = text.replace("               ", "")
        text = text.replace("           ", "")

        matched = document_pattern.findall(text)
        if len(matched) > 0 and len(matched[0]) > 0:
            return matched[0][0]
    return ""


def extract_pdf_link_from_string(text: str) -> str:
    text = text.replace("\n", "")
    text = text.replace("               ", "")
    text = text.replace("           ", "")

    matched = html_pattern.findall(text)
    if len(matched) > 0 and len(matched[0]) > 0:
        return matched[0][0]

    return ""
