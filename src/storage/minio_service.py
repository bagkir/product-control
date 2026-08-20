import os
from datetime import timedelta

from minio import Minio

from src.core.config import settings


class MinIOService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def upload_file(
        self,
        bucket: str,
        file_path: str,
        object_name: str | None = None,
        expires_days: int = 7,
    ) -> str:
        """
        Загрузить файл в MinIO и вернуть pre-signed URL для скачивания.

        Синхронный клиент (minio-py не asyncio) — вызывается из Celery-задачи,
        которая сама уже sync-обёртка над asyncio.run(), так что блокировка
        здесь не мешает остальному приложению (FastAPI её не видит).
        """
        if object_name is None:
            object_name = os.path.basename(file_path)

        self._ensure_bucket(bucket)

        self.client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=file_path,
            content_type=self._get_content_type(file_path),
        )

        return self.client.presigned_get_object(
            bucket_name=bucket,
            object_name=object_name,
            expires=timedelta(days=expires_days),
        )

    def _ensure_bucket(self, bucket: str) -> None:
        """
        Не полагаемся только на то, что init_minio.py успешно отработал при
        старте compose — если бакета почему-то нет (упал init-джоб, кто-то
        удалил бакет руками), создаём его лениво перед первой загрузкой.
        """
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def download_file(self, bucket: str, object_name: str, file_path: str) -> None:
        """Скачать файл из MinIO."""
        self.client.fget_object(
            bucket_name=bucket, object_name=object_name, file_path=file_path
        )

    def delete_file(self, bucket: str, object_name: str) -> None:
        self.client.remove_object(bucket, object_name)

    def list_files(self, bucket: str, prefix: str | None = None):
        return self.client.list_objects(
            bucket_name=bucket,
            prefix=prefix,
            recursive=True,
        )

    @staticmethod
    def _get_content_type(file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
            ".json": "application/json",
        }
        return content_types.get(ext, "application/octet-stream")
