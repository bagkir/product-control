from minio import Minio

from core.config import settings

BUCKETS = {
    "reports": "Сгенерированные отчеты",
    "exports": "Экспортированные данные",
    "imports": "Загруженные файлы для импорта",
}


def get_minio_client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def initialize_minio_buckets() -> None:
    minio_client = get_minio_client()

    for bucket_name, description in BUCKETS.items():
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)
            print(f"✅ Created bucket: {bucket_name} ({description})")
        else:
            print(f"— Bucket already exists: {bucket_name} ({description})")


if __name__ == "__main__":
    initialize_minio_buckets()
