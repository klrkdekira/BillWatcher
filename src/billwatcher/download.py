from http.cookiejar import MozillaCookieJar
from typing import AsyncIterator

import httpx
from faker import Faker

from billwatcher.config import COOKIE_PATH
from billwatcher.types import Language

DOMAIN = "https://www.parlimen.gov.my"
DOCUMENT_PATH = "/bills-dewan-rakyat.html"
DOCUMENT_URL = f"{DOMAIN}{DOCUMENT_PATH}"

fake = Faker()


class BaseDownloader:
    def __init__(self, lang: Language):
        self.lang = lang.value == "en" and "en" or "bm"
        self.transport = httpx.AsyncHTTPTransport(retries=1)
        self.cookies = MozillaCookieJar(COOKIE_PATH)

    def headers(self):
        return {
            "User-Agent": fake.user_agent(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
        }

    async def download_bill(self, path: str) -> AsyncIterator[bytes]:
        self.cookies.load(ignore_discard=True, ignore_expires=True)

        async with httpx.AsyncClient(
            transport=self.transport,
            timeout=300,
            cookies=self.cookies,
        ) as client:
            target = httpx.URL(f"{DOMAIN}{path}")
            req = client.build_request(
                "GET",
                target,
                headers={
                    "User-Agent": fake.user_agent(),
                    "Accept": "application/pdf",
                    "Content-Type": "application/pdf",
                },
            )

            resp = await client.send(req, follow_redirects=True)
            resp.raise_for_status()

            self.cookies.save(ignore_discard=True, ignore_expires=True)

            if resp.headers.get(
                "content-transfer-encoding"
            ) != "binary" or resp.headers.get("content-type") not in (
                "application/octet-stream",
                "application/pdf",
            ):
                raise ValueError(
                    f"Invalid content-type: {resp.headers.get('content-type')}"
                )

            async for chunk in resp.aiter_bytes():
                yield chunk


class ArchiveDownloader(BaseDownloader):
    def __init__(self, lang: Language):
        super().__init__(lang)

    async def download_archive_index(self) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(
            headers=self.headers(),
            transport=self.transport,
            timeout=30,
            cookies=self.cookies,
        ) as client:
            params = {
                "uweb": "dr",
                "lang": self.lang,
                "arkib": "yes",
                "ajx": "0",
            }

            req = client.build_request(
                "GET",
                DOCUMENT_URL,
                params=params,
            )

            resp = await client.send(req, follow_redirects=True)
            resp.raise_for_status()

            self.cookies.save(ignore_discard=True, ignore_expires=True)

            async for chunk in resp.aiter_bytes():
                yield chunk

    async def download_archive_year(self, year: int) -> AsyncIterator[bytes]:
        self.cookies.load(ignore_discard=True, ignore_expires=True)

        async with httpx.AsyncClient(
            headers=self.headers(),
            transport=self.transport,
            timeout=30,
            cookies=self.cookies,
        ) as client:
            params = {
                "uweb": "dr",
                "lang": self.lang,
                "arkib": "yes",
                "ajx": "1",
                "id": f"0_{year}",
            }

            req = client.build_request("GET", DOCUMENT_URL, params=params)

            resp = await client.send(req, follow_redirects=True)
            resp.raise_for_status()

            self.cookies.save(ignore_discard=True, ignore_expires=True)

            async for chunk in resp.aiter_bytes():
                yield chunk


class LiveDownloader(BaseDownloader):
    def __init__(self, lang: Language):
        super().__init__(lang)

    async def download_index(self) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(
            headers=self.headers(),
            transport=self.transport,
            timeout=30,
            cookies=self.cookies,
        ) as client:
            params = {
                "uweb": "dr",
                "lang": self.lang,
            }

            req = client.build_request(
                "GET",
                DOCUMENT_URL,
                params=params,
            )

            resp = await client.send(req, follow_redirects=True)
            resp.raise_for_status()

            self.cookies.save(ignore_discard=True, ignore_expires=True)

            async for chunk in resp.aiter_bytes():
                yield chunk

    # async def download_archive_year(self, year: int) -> AsyncIterator[bytes]:
    #     self.cookies.load(ignore_discard=True, ignore_expires=True)

    #     async with httpx.AsyncClient(
    #         headers=self.headers(),
    #         transport=self.transport,
    #         timeout=30,
    #         cookies=self.cookies,
    #     ) as client:
    #         params = {
    #             "uweb": "dr",
    #             "lang": self.lang,
    #             "arkib": "yes",
    #             "ajx": "1",
    #             "id": f"0_{year}",
    #         }

    #         req = client.build_request("GET", DOCUMENT_URL, params=params)

    #         resp = await client.send(req, follow_redirects=True)
    #         resp.raise_for_status()

    #         self.cookies.save(ignore_discard=True, ignore_expires=True)

    #         async for chunk in resp.aiter_bytes():
    #             yield chunk
