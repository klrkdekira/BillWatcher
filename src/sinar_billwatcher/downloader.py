import enum
import hashlib
from dataclasses import dataclass

import httpx

DOMAIN = "https://www.parlimen.gov.my"


@dataclass(init=True, frozen=True)
class Response:
    data: str
    hash: str
    url: str


class Language(enum.Enum):
    EN = "en"
    BM = "bm"


def fingerprint(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def download_archive_xml(lang: Language) -> Response:
    params = {
        "uweb": "dr",
        "lang": lang.value,
        "arkib": "yes",
        "ajx": "0",
    }

    url = f"{DOMAIN}/bills-dewan-rakyat.html"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
    }

    print(url)

    with httpx.Client(headers=headers) as client:
        try:
            req = client.build_request("GET", url, params=params)
            print(req.url)

            resp = client.send(req)

            return Response(
                data=resp.text,
                hash=fingerprint(resp.text),
                url=str(resp.url),
            )
        except Exception as e:
            raise e
        finally:
            client.close()
