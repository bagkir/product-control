from src.core.exceptions import AlreadyExistsException, NotFoundException, AppException


class BatchNotFoundException(NotFoundException):
    """Партия не найдена."""

    def __init__(self, batch_id: int):
        super().__init__(resource="Batch", identifier=batch_id)


class BatchAlreadyExistsException(AlreadyExistsException):
    """Партия с таким идентификатором (batch_number + batch_date) уже существует."""

    def __init__(self, batch_number: int, batch_date):
        super().__init__(
            resource="Batch",
            identifier=f"{batch_number}/{batch_date}",
        )


class WorkCenterNotFoundException(NotFoundException):
    """Рабочий центр с данным ИдентификаторРЦ не найден."""

    def __init__(self, identifier: str):
        super().__init__(resource="WorkCenter", identifier=identifier)


class BatchMoreThen100(AppException):
    """
    Партия содержит больше 100 продуктов — синхронная агрегация
    (POST /batches/{id}/aggregate) не предназначена для такого объёма,
    нужно использовать POST /batches/{id}/aggregate-async.
    """

    def __init__(self, batch_id: int, count: int):
        super().__init__(
            message=(
                f"Batch {batch_id} has {count} products (>100) — "
                f"use POST /batches/{batch_id}/aggregate-async instead"
            ),
            status_code=400,
        )
