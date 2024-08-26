from typing import Any

import anyio
import pymupdf
import pymupdf4llm

from billwatcher.config import traverse_bill

METADATA_FILE = "metadata.json"
DOCUMENT_FILE = "bill.pdf"
MARKDOWN_FILE = "bill.md"


async def main(*args: Any, **kwargs: Any) -> None:
    for bill in traverse_bill():
        markdown_path = bill / MARKDOWN_FILE
        if markdown_path.exists():
            if markdown_path.stat().st_size > 0:
                # print(f"skipping {bill}, already processed")
                continue

        pdf_path = bill / DOCUMENT_FILE
        if not pdf_path.exists():
            print(f"no pdf file {pdf_path}, skipping")
            continue

        if pdf_path.stat().st_size == 0:
            print(f"empty pdf file {pdf_path}, skipping")
            continue

        print(f"processing {bill}")

        try:
            md = pymupdf4llm.to_markdown(pdf_path)
        except pymupdf.EmptyFileError:
            print(f"empty file {pdf_path}, skipping")
            continue

        metadata_path = bill / METADATA_FILE
        async with await anyio.open_file(metadata_path, "r") as f:
            metadata = await f.read()

        markdown_path = bill / MARKDOWN_FILE
        async with await anyio.open_file(markdown_path, "w") as f:
            await f.write(metadata)
            await f.write("\n\n")
            await f.write(md)


if __name__ == "__main__":
    anyio.run(main, backend="trio")
