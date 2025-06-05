import enum
from dataclasses import dataclass
from typing import List, TypedDict

import httpx


class Language(enum.Enum):
    EN = "en"
    MS = "ms"


class BillStatus(enum.Enum):
    Archive = "archive"
    Live = "live"


@dataclass(init=True, frozen=True)
class Response:
    data: str
    hash: str
    url: str


class DocumentChild(TypedDict):
    id: str
    text: str


class Metadata(TypedDict):
    year: int
    bill: str
    id: str
    children: List[DocumentChild]
    document: str


def flatten_metadata(metadata: Metadata) -> str:
    text = "---\n"
    text += f"Year: {metadata['year']}\n"
    text += f"Bill: {metadata['bill']}\n"
    text += f"Title: {metadata['bill']}\n"

    link = str(httpx.URL(f"https://www.parlimen.gov.my{metadata['document']}"))
    text += f"Download URL: {link}\n"
    text += f"URL: {link}\n"
    text += "---\n"

    text += "---\n"
    text += "Reading:\n"
    for child in metadata["children"]:
        text += f"{child['text']}\n"
    text += "---\n"
    text += "\n"

    return text
