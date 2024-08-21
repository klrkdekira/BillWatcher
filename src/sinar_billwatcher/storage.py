from minio import Minio

BUCKET = "billwatcher"


def connect_s3(endpoint: str, access_key: str, secret_key: str) -> Minio:
    client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
        region="us-east-1",
    )

    found = client.bucket_exists("billwatcher")
    if not found:
        client.make_bucket("billwatcher")

    return client
