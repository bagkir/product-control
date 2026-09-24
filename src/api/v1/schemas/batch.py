from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from src.api.v1.schemas.product import ProductShortResponse


class BatchCreate(BaseModel):
    is_closed: bool = Field(
        default=False,
        validation_alias="СтатусЗакрытия",
    )
    task_description: str = Field(
        validation_alias="ПредставлениеЗаданияНаСмену",
    )
    work_center: str = Field(
        validation_alias="РабочийЦентр",
    )
    shift: str = Field(
        validation_alias="Смена",
    )
    team: str = Field(
        validation_alias="Бригада",
    )
    batch_number: int = Field(
        validation_alias="НомерПартии",
    )
    batch_date: date = Field(
        validation_alias="ДатаПартии",
    )
    nomenclature: str = Field(
        validation_alias="Номенклатура",
    )
    ekn_code: str = Field(
        validation_alias="КодЕКН",
    )
    work_center_identifier: str = Field(
        validation_alias="ИдентификаторРЦ",
    )
    shift_start: datetime = Field(
        validation_alias="ДатаВремяНачалаСмены",
    )
    shift_end: datetime = Field(
        validation_alias="ДатаВремяОкончанияСмены",
    )
    model_config = ConfigDict(populate_by_name=True)


class BatchUpdate(BaseModel):
    is_closed: bool | None = Field(
        default=None,
        validation_alias="СтатусЗакрытия",
    )
    task_description: str | None = Field(
        default=None,
        validation_alias="ПредставлениеЗаданияНаСмену",
    )
    shift: str | None = Field(
        default=None,
        validation_alias="Смена",
    )
    team: str | None = Field(
        default=None,
        validation_alias="Бригада",
    )
    nomenclature: str | None = Field(
        default=None,
        validation_alias="Номенклатура",
    )
    ekn_code: str | None = Field(
        default=None,
        validation_alias="КодЕКН",
    )
    shift_start: datetime | None = Field(
        default=None,
        validation_alias="ДатаВремяНачалаСмены",
    )
    shift_end: datetime | None = Field(
        default=None,
        validation_alias="ДатаВремяОкончанияСмены",
    )
    model_config = ConfigDict(populate_by_name=True)


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_closed: bool
    closed_at: datetime | None
    task_description: str
    work_center_id: int
    shift: str
    team: str
    batch_number: int
    batch_date: date
    nomenclature: str
    ekn_code: str
    shift_start: datetime
    shift_end: datetime
    created_at: datetime
    updated_at: datetime
    products: list[ProductShortResponse]


class BatchFilter(BaseModel):
    is_closed: bool | None = None
    batch_number: int | None = None
    batch_date: date | None = None
    work_center_id: int | None = None
    shift: str | None = None

    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class BatchListResponse(BaseModel):
    items: list[BatchResponse]
    total: int
    offset: int
    limit: int


class BatchExportFilters(BaseModel):
    is_closed: bool | None = None
    batch_number: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    work_center_id: int | None = None
    shift: str | None = None


class BatchExportRequest(BaseModel):
    format: str = Field(default="excel", pattern="^(excel|csv)$")
    filters: BatchExportFilters = Field(default_factory=BatchExportFilters)


class AggregationResponse(BaseModel):
    status: str
    total_products: int
    aggregated: int
    already_aggregated: int
