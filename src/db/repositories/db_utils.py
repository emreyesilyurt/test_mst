import asyncio
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.product_repository import ProductRepository
from models import Product

async def get_products(
    session: AsyncSession,
    **filters
) -> List[Product]:
    """
    Retrieve products matching filters.

    Example:
        products = await get_products(session, category_id=5)
    """
    repo = ProductRepository(session)
    return await repo.list(**filters)

async def save_products_parallel(
    session: AsyncSession,
    products: List[Product]
) -> List[Product]:
    """
    Save a list of Product instances concurrently.

    Commits each via repository.add in parallel.
    """
    repo = ProductRepository(session)
    tasks = [repo.add(product) for product in products]
    saved = await asyncio.gather(*tasks)
    return saved

async def save_products_bulk(
    session: AsyncSession,
    products: List[Product]
) -> None:
    """
    Bulk save products in one transaction for efficiency.
    """
    session.add_all(products)
    await session.commit()

# Example usage
# async with AsyncSessionLocal() as session:
#     # Fetch by filter
#     prods = await get_products(session, manufacturer_id=2)
#     # Update list or create new Product instances
#     new_prods = [Product(part_number=p.part_number+"_v2") for p in prods]
#     # Save in parallel
#     saved = await save_products_parallel(session, new_prods)
#     # Or bulk save
#     await save_products_bulk(session, new_prods)

# ------------------------
# Advanced Filters Example
from sqlalchemy import select, and_, or_
from datetime import datetime

from typing import Optional
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from sqlalchemy import or_, and_, select

async def get_products_advanced(
    session: AsyncSession,
    category_id: Optional[UUID] = None,
    manufacturer_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    title_like: Optional[str] = None,
    use_or: bool = False
) -> List[Product]:
    """
    Retrieve products with complex filters:
      - Combine conditions with AND (default) or OR if use_or=True
      - Date range filter on created_date
      - Partial match on title using LIKE
    """
    conditions = []
    if category_id is not None:
        conditions.append(Product.category_id == category_id)
    if manufacturer_id is not None:
        conditions.append(Product.manufacturer_id == manufacturer_id)
    if start_date and end_date:
        conditions.append(Product.created_date.between(start_date, end_date))
    if title_like:
        conditions.append(Product.title.ilike(f"%{title_like}%"))

    # Choose logical operator
    if conditions:
        operator = or_ if use_or else and_
        stmt = select(Product).where(operator(*conditions))
    else:
        stmt = select(Product)

    result = await session.scalars(stmt)
    return result.all()

# Example advanced usage
# async with AsyncSessionLocal() as session:
#     # AND combination (default)
#     products = await get_products_advanced(
#         session,
#         category_id=3,
#         start_date=datetime(2025,1,1),
#         end_date=datetime(2025,6,30),
#         title_like="Widget"
#     )
#     # OR combination
#     products_or = await get_products_advanced(
#         session,
#         category_id=3,
#         manufacturer_id=5,
#         use_or=True
#     )
""
