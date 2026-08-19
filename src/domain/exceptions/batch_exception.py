from src.core.exceptions import AlreadyExistsException, NotFoundException


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


# src/domain/exceptions/batch_exception.py


class BatchMoreThen100(Exception):
    def __init__(self, batch_id: int, count: int):
        self.batch_id = batch_id
        self.count = count
        super().__init__(
            f"Batch {batch_id} has {count} products, which exceeds 100. Use async aggregation endpoint."
        )
