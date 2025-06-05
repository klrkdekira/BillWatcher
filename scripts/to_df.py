import json
from datetime import datetime
from zoneinfo import ZoneInfo

import polars as pl

from billwatcher.config import traverse_bill

METADATA_FILE = "metadata.json"
DOCUMENT_FILE = "bill.pdf"
MARKDOWN_FILE = "bill.md"

df = pl.DataFrame(
    {
        "url": [],
        "content": [],
        "metadata": [],
        "signature": [],
        "raw": [],
        "last_updated": [],
        "summary": [],
        "qa_pairs": [],
        "language": [],
    },
    schema={
        "url": pl.String,
        "content": pl.String,
        "metadata": pl.String,
        "signature": pl.String,
        "raw": pl.String,
        "last_updated": pl.Datetime(time_unit="us", time_zone="UTC"),
        "summary": pl.String,
        "qa_pairs": pl.String,
        "language": pl.String,
    },
)


now = datetime.now().replace(tzinfo=ZoneInfo("Asia/Kuala_Lumpur"))


# Add helper function after imports
def get_language_from_path(bill_path):
    """Extract language from bill path. Expected format: .../ms/... or .../en/..."""
    parts = bill_path.parts
    for part in parts:
        if part in ("ms", "en"):
            return part
    return "unknown"


for bill in traverse_bill():
    markdown_path = bill / MARKDOWN_FILE
    if not markdown_path.exists():
        continue

    metadata_path = bill / METADATA_FILE
    if not metadata_path.exists():
        continue

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    with open(markdown_path, "r") as f:
        content = f.read()

    language = get_language_from_path(bill)
    metadata["language"] = language

    row = pl.DataFrame(
        {
            "url": [metadata["bill"]],
            "content": [content],
            "metadata": [json.dumps(metadata)],
            "signature": [""],
            "raw": [""],
            "last_updated": [now],
            "summary": [""],
            "qa_pairs": [""],
            "language": [language],
        },
        schema={
            "url": pl.String,
            "content": pl.String,
            "metadata": pl.String,
            "signature": pl.String,
            "raw": pl.String,
            "last_updated": pl.Datetime(time_unit="us", time_zone="UTC"),
            "summary": pl.String,
            "qa_pairs": pl.String,
            "language": pl.String,
        },
    )
    df = df.vstack(row)

df.write_parquet("billwatcher.parquet")
