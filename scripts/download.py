import io
import os
import sys

from sqlalchemy import exists

from billwatcher.download import download_archive_xml
from billwatcher.model import Document, connect_db
from billwatcher.storage import connect_s3
from billwatcher.types import Language


def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    Session = connect_db(dsn)

    s3_endpoint = "{}:{}".format(
        os.environ.get("CONTAINER_INTERFACE"), os.environ.get("MINIO_PORT")
    )
    s3_access_key = os.environ.get("MINIO_ROOT_USER") or ""
    s3_secret_key = os.environ.get("MINIO_ROOT_PASSWORD") or ""

    s3 = connect_s3(
        endpoint=s3_endpoint,
        access_key=s3_access_key,
        secret_key=s3_secret_key,
    )

    with Session() as session:
        try:
            response = download_archive_xml(Language.EN)
            data_exists = session.query(
                exists().where(Document.file_hash == response.hash)
            ).scalar()
            if not data_exists:
                s3.put_object(
                    "billwatcher",
                    response.hash,
                    io.BytesIO(response.data.encode("utf-8")),
                    len(response.data),
                )

                doc = Document()
                doc.title = "root_en"
                doc.file_source = response.url
                doc.file_hash = response.hash
                doc.file_name = response.url
                doc.file_id = response.hash

                session.add(doc)
                session.commit()
        except Exception as e:
            print(e, file=sys.stderr)
            session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    main()
