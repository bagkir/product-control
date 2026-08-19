from fastapi import APIRouter, status

from src.api.dependencies import ApiKeyDep, ProductServiceDep
from src.api.v1.schemas.product import ProductCreate, ProductShortResponse

router = APIRouter(prefix="/products", tags=["products"], dependencies=[ApiKeyDep])


@router.post(
    "", response_model=ProductShortResponse, status_code=status.HTTP_201_CREATED
)
async def create_products(payload: ProductCreate, service: ProductServiceDep):
    """
    Добавление продукции POST /api/v1/products
    """
    return await service.create_product(payload)
