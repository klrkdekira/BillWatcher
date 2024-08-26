import enum
from dataclasses import dataclass
from typing import List, TypedDict


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
