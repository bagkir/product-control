from datetime import date
from typing import Literal

from pydantic import BaseModel


class ImportProgress(BaseModel):
    current: int
    total: int
    created: int
    skipped: int


class ImportError(BaseModel):
    row: int
    error: str


class ImportResult(BaseModel):
    success: bool
    total_rows: int
    created: int
    skipped: int
    errors: list[ImportError]


ExportFormat = Literal["excel", "csv"]


class ExportFilters(BaseModel):
    is_closed: bool | None = None
    date_from: date | None = None
    date_to: date | None = None
    work_center_id: int | None = None
    shift: str | None = None


class ExportCreate(BaseModel):
    format: ExportFormat = "excel"
    filters: ExportFilters = ExportFilters()


class ExportResult(BaseModel):
    success: bool
    file_url: str
    total_batches: int
