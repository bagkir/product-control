from src.api.v1.schemas.product import ProductCreate
from src.data.repositories import BatchRepository
from src.data.repositories.product_repository import ProductRepository
from src.domain.exceptions.product_exception import (
    ProductAlreadyExistsException,
)
from src.domain.services.webhook_service import WebhookService


class ProductService:
    def __init__(
        self,
        product_repository: ProductRepository,
        batch_repository: BatchRepository,
        webhook_service: WebhookService,
    ):
        self.product_repository = product_repository
        self.batch_repository = batch_repository
        self.webhook_service = webhook_service

    async def create_product(
        self,
        data: ProductCreate,
    ):
        product = await self.product_repository.get_by_unique_code(data.unique_code)

        if product:
            raise ProductAlreadyExistsException(data.unique_code)

        return await self.product_repository.create(
            unique_code=data.unique_code,
            batch_id=data.batch_id,
        )

    async def aggregate_product(
        self,
        unique_code: str,
    ):
        product = await self.product_repository.get_by_unique_code(unique_code)

        if product is None:
            raise ValueError(f"Product {unique_code} not found")

        if product.is_aggregated:
            return product

        product = await self.product_repository.aggregate_product(unique_code)
        batch = await self.batch_repository.get_by_id(product.batch_id)
        await self.webhook_service.publish_event(
            event_type="product_aggregated",
            data={
                "unique_code": product.unique_code,
                "batch_id": product.batch_id,
                "batch_number": batch.batch_number,
                "aggregated_at": product.aggregated_at.isoformat(),
            },
        )

        return product
