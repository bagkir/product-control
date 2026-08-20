from typing import Annotated

from fastapi import APIRouter, Query, UploadFile, status

from src.api.dependencies import ApiKeyDep, BatchServiceDep
from src.api.v1.schemas.batch import (
    BatchCreate,
    BatchExportRequest,
    BatchFilter,
    BatchListResponse,
    BatchResponse,
    BatchUpdate,
    AggregationResponse,
)
from src.api.v1.schemas.product import AggregateAsyncRequest
from src.api.v1.schemas.report import ReportCreate
from src.api.v1.schemas.task import TaskResponse

router = APIRouter(prefix="/batches", tags=["batches"], dependencies=[ApiKeyDep])


@router.post(
    "", response_model=list[BatchResponse], status_code=status.HTTP_201_CREATED
)
async def create_batches(payload: list[BatchCreate], service: BatchServiceDep):
    """
    Создание сменных заданий.
    """
    return await service.create_batches(payload)


@router.get("/{batch_id}", response_model=BatchResponse, status_code=status.HTTP_200_OK)
async def get_batch(batch_id: int, service: BatchServiceDep):
    return await service.get_batch(batch_id)


@router.patch("/{batch_id}", response_model=BatchResponse)
async def update_batch(batch_id: int, payload: BatchUpdate, service: BatchServiceDep):
    return await service.update_batch(batch_id, payload)


@router.get("", response_model=BatchListResponse)
async def list_batches(
    service: BatchServiceDep,
    filters: Annotated[BatchFilter, Query()],
):
    result = await service.list_batches(filters)
    return BatchListResponse(
        items=result["items"],
        total=result["total"],
        offset=filters.offset,
        limit=filters.limit,
    )


@router.post(
    path="/{batch_id}/aggregate",
    response_model=AggregationResponse,
    status_code=status.HTTP_200_OK,
)
async def aggregate_batch(
    batch_id: int,
    service: BatchServiceDep,
):
    return await service.aggregate_batch(batch_id=batch_id)


@router.post(
    path="/{batch_id}/aggregate-async",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def aggregate_batch_async(
    batch_id: int,
    payload: AggregateAsyncRequest,
    service: BatchServiceDep,
):
    """
    POST /api/v1/batches/{batch_id}/aggregate-async
    Для >100 единиц продукции — ставит задачу в очередь и сразу возвращает task_id.
    """
    return await service.start_aggregate_async(batch_id, payload.unique_codes)


@router.post(
    path="/{batch_id}/reports",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_batch_report(
    batch_id: int,
    payload: ReportCreate,
    service: BatchServiceDep,
):
    """
    POST /api/v1/batches/{batch_id}/reports
    """
    return await service.start_generate_report(batch_id, payload)


@router.post(
    "/import",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_batches(
    file: UploadFile,
    service: BatchServiceDep,
):
    return await service.start_import(file)


@router.post(
    "/export",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def export_batches(
    payload: BatchExportRequest,
    service: BatchServiceDep,
):
    return await service.start_export(payload)
