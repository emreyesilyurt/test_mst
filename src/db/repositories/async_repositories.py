"""
Asynchronous repository module for database interactions in master_electronics.
This module provides async repository classes for CRUD operations on database models using SQLAlchemy async sessions.
"""

from typing import Generic, TypeVar, Type, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update as sqlalchemy_update, delete as sqlalchemy_delete
from src.db.models import (
    Product, PartNumber, Manufacturer, Category, Attribute,
    CategoryAttribute, DocumentMedia, ProductSeller,
    ProductAttribute, ProductExtra, AutomationTask
)

T = TypeVar('T')

class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def add(self, instance: T) -> T:
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def get(self, id: int) -> Optional[T]:
        return await self.session.get(self.model, id)

    async def list(self, **filters) -> List[T]:
        stmt = select(self.model)
        if filters:
            stmt = stmt.filter_by(**filters)
        result = await self.session.scalars(stmt)
        return result.all()

    async def update(self, id: int, **attrs) -> Optional[T]:
        instance = await self.get(id)
        if not instance:
            return None
        for key, value in attrs.items():
            setattr(instance, key, value)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        instance = await self.get(id)
        if not instance:
            return False
        await self.session.delete(instance)
        await self.session.commit()
        return True


class ProductRepository(BaseRepository[Product]):
    def __init__(self, session):
        super().__init__(session, Product)


class PartNumberRepository(BaseRepository[PartNumber]):
    def __init__(self, session):
        super().__init__(session, PartNumber)


class ManufacturerRepository(BaseRepository[Manufacturer]):
    def __init__(self, session):
        super().__init__(session, Manufacturer)


from sqlalchemy.dialects.postgresql import UUID
import uuid

class CategoryRepository(BaseRepository[Category]):
    def __init__(self, session):
        super().__init__(session, Category)

    async def get(self, id) -> Category | None:
        return await self.session.get(self.model, id)

    async def update(self, id, **attrs) -> Category | None:
        instance = await self.get(id)
        if not instance:
            return None
        for key, value in attrs.items():
            setattr(instance, key, value)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id) -> bool:
        instance = await self.get(id)
        if not instance:
            return False
        await self.session.delete(instance)
        await self.session.commit()
        return True

    async def get_categories(self, level: int, parent_filter=None) -> list[Category]:
        stmt = select(self.model).filter(self.model.depth == level)
        if parent_filter:
            stmt = stmt.filter(self.model.parent_id == parent_filter)
        result = await self.session.execute(stmt)
        scalars = result.scalars()
        return scalars.all()


    async def get_categories_by_name(self, name: str, parent_filter=None) -> Category | None:
        stmt = select(self.model).filter(self.model.name == name)
        if parent_filter:
            stmt = stmt.filter(self.model.parent_id == parent_filter)
        result = await self.session.execute(stmt)
        scalars = result.scalars()
        return scalars.first()



class AttributeRepository(BaseRepository[Attribute]):
    def __init__(self, session):
        super().__init__(session, Attribute)


class CategoryAttributeRepository(BaseRepository[CategoryAttribute]):
    def __init__(self, session):
        super().__init__(session, CategoryAttribute)


class DocumentMediaRepository(BaseRepository[DocumentMedia]):
    def __init__(self, session):
        super().__init__(session, DocumentMedia)


class ProductSellerRepository(BaseRepository[ProductSeller]):
    def __init__(self, session):
        super().__init__(session, ProductSeller)


class ProductAttributeRepository(BaseRepository[ProductAttribute]):
    def __init__(self, session):
        super().__init__(session, ProductAttribute)


class ProductExtraRepository(BaseRepository[ProductExtra]):
    def __init__(self, session):
        super().__init__(session, ProductExtra)


class ManualTaskRepository(BaseRepository[AutomationTask]):
    def __init__(self, session):
        super().__init__(session, AutomationTask)

def get_session():
    """
    Create and return a new async SQLAlchemy session using the configured async engine.
    
    Returns:
        AsyncSession: A new async SQLAlchemy session.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from src.db.connections import get_supabase_async_engine
    
    engine = get_supabase_async_engine()
    AsyncSessionFactory = async_sessionmaker(bind=engine)
    return AsyncSessionFactory()


async def main():
    """
    Placeholder for async repository testing or initialization.
    This function can be implemented with an async engine and session setup as needed.
    """
    print("Async repository main function placeholder. Implement async engine setup as required.")
    return


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
