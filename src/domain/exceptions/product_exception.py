from src.core.exceptions import AlreadyExistsException


class ProductAlreadyExistsException(AlreadyExistsException):
    def __init__(self, unique_code: str):
        super().__init__(resource="Product", identifier=unique_code)
