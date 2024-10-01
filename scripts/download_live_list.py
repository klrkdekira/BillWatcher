import json
import re
import sys
from typing import Any, List, Tuple

import anyio
from bs4 import BeautifulSoup

from billwatcher.config import DocumentPath
from billwatcher.download import LiveDownloader
from billwatcher.types import BillStatus, Language, Metadata
from billwatcher.utils import extract_pdf_link_from_string

lang: Language = Language.EN
bill_status: BillStatus = BillStatus.Live


bill_id_pattern = re.compile(r".*(\d+)\/(\d{4})")


async def main(*args: Any, **kwargs: Any) -> None:
    downloader = LiveDownloader(lang)
    document_path = DocumentPath(lang, bill_status)

    live_list = document_path.list()
    # do not skip this step, this is to populate the cookiejar
    print(f"downloading live list, {live_list}")
    async with await anyio.open_file(live_list, "wb") as f:
        async for chunk in downloader.download_index():
            await f.write(chunk)

    soup = BeautifulSoup(live_list.read_text(), "html.parser")

    bill_list: List[Tuple[int, str, str]] = []
    year_dict: dict[int, List[Metadata]] = {}

    rows = soup.select("table#ruulist > tbody > tr")
    for row in rows:
        cells = row.findChildren("td", recursive=False)
        if len(cells) < 4:
            print("skipping row with less than 4 cells")
            continue

        bill_id = cells[0].text.strip()
        matches = bill_id_pattern.findall(bill_id)
        if not matches:
            print(f"skipping row with invalid bill id {bill_id}")
            continue

        bill_code = f"{matches[0][1]}_{matches[0][0]}"

        item: Metadata = {
            "year": int(cells[1].text.strip()),
            "bill": f"{bill_id} - {cells[2].text.strip()}",
            "id": bill_code,
            "children": [],
            "document": "",
        }

        item["children"].append({"id": "full_text", "text": cells[3].text.strip()})

        link = cells[0].find("a")
        if link:
            doc_link = link.attrs.get("onclick")
            if doc_link:
                item["document"] = extract_pdf_link_from_string(doc_link)

        div = cells[3].find("div")
        if div:
            item["children"].append({"id": "status", "text": div.text.strip()})

        title = cells[3].find("h1")
        if title:
            item["children"].append({"id": "title", "text": title.text.strip()})

        table = cells[3].select("table > tr")
        for tr in table:
            tds = tr.findChildren("td", recursive=False)
            if len(tds) < 3:
                print("skipping tr with less than 3 tds")
                continue

            item["children"].append(
                {"id": tds[0].text.strip(), "text": tds[2].text.strip()}
            )

        if item["year"] not in year_dict:
            year_dict[item["year"]] = []

        year_dict[item["year"]].append(item)
        bill_list.append((item["year"], item["id"], item["document"]))

    for year, metadata_list in year_dict.items():
        path = document_path.year_list(year)
        async with await anyio.open_file(path, "w") as f:
            await f.write(json.dumps(metadata_list, indent=2))

        for metadata in metadata_list:
            path = document_path.bill_metadata(year, metadata["id"])
            async with await anyio.open_file(path, "w") as f:
                await f.write(json.dumps(metadata, indent=2))

    for year, id, document in bill_list:
        path = document_path.bill_document(year, id)

        if not document:
            print(f"no document found for {year}/{id}, {document}")
            continue

        if not document.endswith(".pdf") and not document.endswith(".PDF"):
            print(f"skipping non-pdf document {year}/{id}, {document}")
            continue

        if not path.exists() or path.stat().st_size <= 30:
            print(f"downloading bill {year}/{id}, {path}, {document}")
            try:
                async with await anyio.open_file(path, "wb") as f:
                    async for chunk in downloader.download_bill(document):
                        await f.write(chunk)
            except Exception as e:
                print(f"failed to download {year}/{id}, {document}, {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "ms":
            lang = Language.MS

    anyio.run(main, backend="trio")
