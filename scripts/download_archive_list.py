import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, List, Tuple

import anyio

from billwatcher.config import DocumentPath
from billwatcher.download import ArchiveDownloader
from billwatcher.types import BillStatus, Language, Metadata
from billwatcher.utils import extract_pdf_link

lang: Language = Language.EN
bill_status: BillStatus = BillStatus.Archive


async def main(*args: Any, **kwargs: Any) -> None:
    downloader = ArchiveDownloader(lang)
    document_path = DocumentPath(lang, bill_status)

    archive_list = document_path.list()
    # do not skip this step, this is to populate the cookiejar
    print(f"downloading archive list, {archive_list}")
    async with await anyio.open_file(archive_list, "wb") as f:
        async for chunk in downloader.download_archive_index():
            await f.write(chunk)

    tree = ET.parse(archive_list)
    root = tree.getroot()

    year_list: List[Tuple[int, Path]] = []

    for item in root:
        year = int(item.attrib["text"])
        archive_index = document_path.year_list(year)
        year_list.append((year, archive_index))

        if not archive_index.exists() or archive_index.stat().st_size == 0:
            print(f"downloading archive year {year}, {archive_index}")
            async with await anyio.open_file(archive_index, "wb") as f:
                async for chunk in downloader.download_archive_year(year):
                    await f.write(chunk)

    bill_list: List[Tuple[int, str, str]] = []

    for year, path in year_list:
        tree = ET.parse(path)
        root = tree.getroot()
        for item in root:
            metadata: Metadata = {
                "year": year,
                "bill": html.unescape(item.attrib["text"].strip()),
                "id": html.unescape(item.attrib["id"].strip()),
                "children": [],
                "document": "",
            }

            path = document_path.bill_metadata(year, metadata["id"])

            for child in item:
                # ignore the first child
                if child.tag == "userdata":
                    metadata["document"] = extract_pdf_link(child)
                    continue

                # first one contains the link
                if child.attrib["id"].endswith("_1"):
                    userdata = child.find("userdata")
                    metadata["document"] = extract_pdf_link(userdata)

                # populate metadata
                metadata["children"].append(
                    {
                        "text": html.unescape(child.attrib["text"].strip()),
                        "id": html.unescape(child.attrib["id"].strip()),
                    }
                )

            bill_list.append((year, metadata["id"], metadata["document"]))

            if not path.exists() or path.stat().st_size == 0:
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
