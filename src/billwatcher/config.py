import pathlib

from billwatcher.types import BillStatus, Language

DATA_DIR = pathlib.Path("scraper_data")
DATA_DIR.mkdir(exist_ok=True)

COOKIE_PATH = DATA_DIR / "cookie.txt"
COOKIE_PATH.touch(exist_ok=True)


class DocumentPath:
    def __init__(self, lang: Language, bill_status: BillStatus):
        self.lang = lang
        self.bill_status = bill_status

        self.dir = DATA_DIR / lang.value / bill_status.value
        self.dir.mkdir(exist_ok=True)

    def list(self) -> pathlib.Path:
        return self.dir / "list.html"

    def year(self, year: int) -> pathlib.Path:
        path = self.dir / str(year)
        path.mkdir(exist_ok=True)

        return path

    def year_list(self, year: int) -> pathlib.Path:
        return self.year(year) / "list.json"

    def bill(self, year: int, bill: str) -> pathlib.Path:
        path = self.year(year) / bill
        path.mkdir(exist_ok=True)

        return path

    def bill_metadata(self, year: int, bill: str) -> pathlib.Path:
        return self.bill(year, bill) / "metadata.json"

    def bill_document(self, year: int, bill: str) -> pathlib.Path:
        return self.bill(year, bill) / "bill.pdf"

    def bill_markdown(self, year: int, bill: str) -> pathlib.Path:
        return self.bill(year, bill) / "bill.md"
