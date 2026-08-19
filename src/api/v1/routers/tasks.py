from celery.result import AsyncResult
from fastapi import APIRouter

from src.api.dependencies import ApiKeyDep
from src.api.v1.schemas.task import TaskProgress, TaskResponse
from src.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[ApiKeyDep])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """
    GET /api/v1/tasks/{task_id}

    Общий эндпоинт для опроса статуса любой Celery-задачи
    (агрегация, отчёты, импорт, экспорт) — все они кладут task_id
    в один и тот же Redis result backend.
    """
    result = AsyncResult(task_id, app=celery_app)

    task_result: dict | TaskProgress | None = None

    if result.state == "PROGRESS":
        info = result.info or {}
        task_result = TaskProgress(
            current=info.get("current", 0),
            total=info.get("total", 0),
            progress=info.get("progress", 0.0),
        )
    elif result.state == "SUCCESS":
        task_result = result.result
    elif result.state == "FAILURE":
        task_result = {"error": str(result.info)}

    return TaskResponse(
        task_id=task_id,
        status=result.state,
        result=task_result,
    )
