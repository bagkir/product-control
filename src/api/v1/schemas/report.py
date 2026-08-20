from datetime import datetime
from typing import Literal

from pydantic import BaseModel

ReportFormat = Literal["excel", "pdf"]


class ReportResult(BaseModel):
    success: bool
    file_url: str
    file_name: str
    file_size: int
    expires_at: datetime


class ReportCreate(BaseModel):
    format: ReportFormat = "excel"
