import time
from minio import Minio
from functools import lru_cache


@lru_cache
def get_minio_client(
    endpoint: str,
    access_key: str,
    secret_key: str,
    secure: bool = False,
) -> Minio:
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def ensure_bucket(client: Minio, bucket_name: str):
    for attempt in range(5):
        try:
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
            return
        except Exception as e:
            if attempt < 4:
                time.sleep(2)
            else:
                raise e
