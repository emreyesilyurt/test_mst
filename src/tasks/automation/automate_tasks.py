"""
Automation script for task operations in master_electronics.
This script handles fetching part number (PN) data from BigQuery and writing results to Supabase PostgreSQL database
using the EeImputeModule from the imputemodule package.
"""

import asyncio
import time
import sys
import os
import logging
# from imputemodule.ee.ee_imputemodule import EeImputeModule

from imputemodule import ImputeModule
from imputemodule.core.config import get_digikey_fast_only_config, FastPathConfig
from imputemodule.core.entities import EntityToImpute


from src.db.connections import get_supabase_async_engine
from src.db.services.bigquery_service import fetch_all_data_sorted
from src.db.repositories.async_repositories import (
    ProductRepository, ManufacturerRepository, PartNumberRepository,
    DocumentMediaRepository, ProductAttributeRepository, ProductExtraRepository,
    CategoryRepository, ProductSellerRepository
)
from src.db.models import (
    Product, Manufacturer, PartNumber, DocumentMedia, ProductAttribute, ProductExtra,
    CategoryAttribute, Attribute, Category, ProductSeller, AutomationTask
)

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, and_, func              
import numpy as np

class TaskAutomator:
    def __init__(self, silent=False):
        # self.impute_module = EeImputeModule()
        self.impute_module = ImputeModule(get_digikey_fast_only_config())
        # Comment out BigQuery client initialization for testing without BigQuery
        # self.bq_client = get_bigquery_client()
        self.ref_id = 0  # Default ref_id for impute operations
        self.source = 'automation'
        self.silent = silent
        self.current_task = None  # Track current automation task
        
        if not silent:
            print("Imported Category, Attribute, and CategoryAttribute models for handling product attributes.")

    async def create_automation_task(self, product_id: int, batch_id: str = None, session: AsyncSession = None):
        """
        Create a new AutomationTask record to track the processing of a product.
        
        Args:
            product_id: The product ID being processed
            batch_id: Optional batch identifier
            session: Database session to use
            
        Returns:
            AutomationTask: The created task record
        """
        should_close_session = session is None
        if session is None:
            async_engine = get_supabase_async_engine()
            AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
            session = AsyncSessionLocal()
        
        try:
            # Create new automation task
            task = AutomationTask()
            task.initialize_task(product_id, batch_id)
            
            session.add(task)
            await session.flush()  # Get the ID
            await session.commit()
            
            # Set ref_id to the task ID for tracking related records
            self.ref_id = task.id
            self.current_task = task
            
            if not self.silent:
                print(f"Created AutomationTask {task.id} for product ID: {product_id}")
            
            return task
            
        except Exception as e:
            await session.rollback()
            print(f"Error creating automation task: {e}")
            raise
        finally:
            if should_close_session:
                await session.close()

    async def update_task_status(self, task_id: int, status_method: str, error_message: str = None, session: AsyncSession = None):
        """
        Update the status of an AutomationTask.
        
        Args:
            task_id: ID of the task to update
            status_method: Method name to call on the task ('start_processing', 'mark_data_finished', etc.)
            error_message: Error message if marking as failed
            session: Database session to use
        """
        should_close_session = session is None
        if session is None:
            async_engine = get_supabase_async_engine()
            AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
            session = AsyncSessionLocal()
        
        try:
            # Get the task
            task = await session.scalar(select(AutomationTask).where(AutomationTask.id == task_id))
            if not task:
                print(f"AutomationTask {task_id} not found")
                return
            
            # Call the appropriate status method
            if status_method == 'start_processing':
                task.start_processing()
            elif status_method == 'mark_data_finished':
                task.mark_data_finished()
            elif status_method == 'mark_supabase_finished':
                task.mark_supabase_finished()
            elif status_method == 'mark_completed':
                task.mark_completed()
            elif status_method == 'mark_failed':
                task.mark_failed(error_message or "Unknown error")
            
            await session.commit()
            
            if not self.silent:
                print(f"Updated AutomationTask {task_id} status to: {task.current_status}")
                
        except Exception as e:
            await session.rollback()
            print(f"Error updating task status: {e}")
            raise
        finally:
            if should_close_session:
                await session.close()

    async def save_impute_op(self, task_id: int, impute_op, session: AsyncSession = None):
        """
        Save the impute_op data to the AutomationTask.
        
        Args:
            task_id: ID of the task to update
            impute_op: The impute operation object to save
            session: Database session to use
        """
        should_close_session = session is None
        if session is None:
            async_engine = get_supabase_async_engine()
            AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
            session = AsyncSessionLocal()
        
        try:
            # Get the task
            task = await session.scalar(select(AutomationTask).where(AutomationTask.id == task_id))
            if not task:
                print(f"AutomationTask {task_id} not found")
                return
            
            # Convert impute_op to serializable format
            impute_op_data = {}
            if impute_op:
                try:
                    # Store scrape results
                    if hasattr(impute_op, 'scrape_results') and impute_op.scrape_results:
                        impute_op_data['scrape_results'] = {}
                        for key, sc in impute_op.scrape_results.items():
                            if hasattr(sc, 'data') and sc.data:
                                impute_op_data['scrape_results'][key] = {
                                    'data': sc.data,
                                    'status': getattr(sc, 'status', None),
                                    'url': getattr(sc, 'url', None)
                                }
                    
                    # Store other relevant attributes
                    if hasattr(impute_op, 'entity'):
                        impute_op_data['entity'] = {
                            'name': getattr(impute_op.entity, 'name', None)
                        }
                    
                    # Store any additional metadata
                    from datetime import datetime
                    impute_op_data['timestamp'] = datetime.now().isoformat()
                    
                except Exception as e:
                    print(f"Error serializing impute_op: {e}")
                    impute_op_data = {'error': f'Failed to serialize impute_op: {str(e)}'}
            
            # Save to database
            task.imputeop = impute_op_data
            await session.commit()
            
            if not self.silent:
                print(f"Saved impute_op data to AutomationTask {task_id}")
                
        except Exception as e:
            await session.rollback()
            print(f"Error saving impute_op: {e}")
            raise
        finally:
            if should_close_session:
                await session.close()

    async def get_mp_category(self, cats, session: AsyncSession):
        """
        Async method to get category using repository pattern with hierarchical parent filtering.

        Args:
            cats: List of category names in hierarchical order.
            session: AsyncSession to use for DB operations.

        Returns:
            The matched Category object or None if not found.
        """
        if not cats or len(cats) == 0:
            return None

        category_repo = CategoryRepository(session)

        ROOT_PARENT_ID = '11111111-1111-1111-1111-111111111111'
        mp_category = None

        cat1 = await category_repo.get_categories_by_name(name=cats[0], parent_filter=ROOT_PARENT_ID)
        if cat1 and len(cats) > 1:
            cat2 = await category_repo.get_categories_by_name(name=cats[1], parent_filter=cat1.id)
            if cat2 is None:
                cat2 = await category_repo.get_categories_by_name(name=f'{cats[1]} - Unassigned', parent_filter=cat1.id)
            if cat2:
                if cat2.product_category:
                    mp_category = cat2
                if len(cats) > 2:
                    cat3 = await category_repo.get_categories_by_name(name=cats[2], parent_filter=cat2.id)
                    if cat3:
                        mp_category = cat3
                    else:
                        if cat2.product_category:
                            mp_category = cat2
                        else:
                            cat3 = await category_repo.get_categories_by_name(name=f'{cats[2]} - Unassigned', parent_filter=cat2.id)
                            if cat3:
                                mp_category = cat3
                else:
                    if len(cats) > 3:
                        cat3 = await category_repo.get_categories_by_name(name=f'{cats[2]} - {cats[3]}', parent_filter=cat2.id)
                        if cat3:
                            mp_category = cat3

        if not mp_category:
            print(f"Category not found for cats: {cats}")
            mp_category = await category_repo.get_categories_by_name(name='Uncategorized', parent_filter=ROOT_PARENT_ID)

        print(f"Category found: {mp_category.fullname if mp_category else 'None'}")
        return mp_category

    async def fetch_pn_data_from_bigquery(self, priority_threshold: float = 0.8, limit: int = 100):
        """
        Fetch part number data from BigQuery based on a priority score threshold.
        Currently disabled for testing without BigQuery.

        Args:
            priority_threshold: The minimum priority score for part numbers to be fetched (default: 0.8).
            limit: The maximum number of part numbers to fetch (default: 100).

        Returns:
            List of data rows from BigQuery, each containing part number and related information.
        """
        print("BigQuery fetch is disabled for testing. Returning empty list.")
        return []

    async def scrape_data_with_impute_module(self, query: str):
        """
        Use EeImputeModule to scrape data for a given query.

        Args:
            query: The part number or search query to send to DigiKey.

        Returns:
            ImputeOp object containing the scraped data.
        """
        impute_op = await self.impute_module.scrape_digikey_query_async(query)
        return impute_op

    async def scrape_data_with_impute_module_v2(self, query: str):
        """
        Use EeImputeModule to scrape data for a given query.

        Args:
            query: The part number or search query to send to DigiKey.

        Returns:
            ImputeOp object containing the scraped data.
        """
        
        entity = EntityToImpute(name=query)

        # https://www.digikey.com/en/products/result?keywords=RGC1A23D15KGU


        impute_op = await self.impute_module.run(
            entity=entity,
            schema=[],  # Schema not needed for fast path
            max_urls=0  # Not used in fast path mode
        )

        return impute_op

    async def test_digikey_search(self, query: str, batch_id: str = None):
        """
        Test function to search DigiKey directly for a given query and write results to Supabase.
        Bypasses BigQuery for testing purposes. Now includes AutomationTask tracking.

        Args:
            query: The part number or search term to query DigiKey with.
            batch_id: Optional batch identifier for tracking

        Returns:
            Result of writing data to Supabase.
        """
        task = None
        async_engine = get_supabase_async_engine()
        AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)
        
        async with AsyncSessionLocal() as session:
            try:
                # First, get or create the product for this part number
                part_number_repo = PartNumberRepository(session)
                pn_records = await part_number_repo.list(name=query)
                
                if not pn_records:
                    # Create new part number
                    pn_record = PartNumber(name=query)
                    session.add(pn_record)
                    await session.flush()
                    await session.commit()
                else:
                    pn_record = pn_records[0]
                
                # Get or create product record
                product = await session.scalar(
                    select(Product).where(Product.part_number == pn_record.product_id)
                )
                
                if not product:
                    # Create new product
                    product = Product(part_number=pn_record.product_id)
                    session.add(product)
                    await session.flush()
                    await session.commit()
                
                # Check if an AutomationTask already exists for this product in this batch
                existing_task = await session.scalar(
                    select(AutomationTask).where(
                        and_(
                            AutomationTask.product_id == product.product_id,
                            AutomationTask.batch_id == batch_id,
                            AutomationTask.current_status != 'failed'
                        )
                    )
                )
                
                if existing_task:
                    # Use existing task
                    task = existing_task
                    self.ref_id = task.id
                    self.current_task = task
                    if not self.silent:
                        print(f"Using existing AutomationTask {task.id} for product ID: {product.product_id}")
                else:
                    # Create new automation task to track this operation
                    task = await self.create_automation_task(product.product_id, batch_id, session)
                    
                    # Mark task as started processing
                    await self.update_task_status(task.id, 'start_processing', session=session)
                
                # Scrape data from DigiKey using the existing method
                impute_op = await self.scrape_data_with_impute_module_v2(query)
                print(f"Scraped data for query: {query}")

                # Save the impute_op data to the automation task
                await self.save_impute_op(task.id, impute_op, session=session)

                # Pass the results directly to write_to_supabase
                # data = impute_op.results if impute_op and impute_op.results else []
                _,sc = next(iter(impute_op.scrape_results.items()))
                data = sc.data if sc and sc.data else []
                
                if data and len(data) > 0:
                    
                    pn_list = []
                    other_pn_names = data[0].get('other_names')
                    if isinstance(other_pn_names, list):
                        for i in other_pn_names:
                            if isinstance(i, str):
                                pn_list.append(i.lower())
                    if data[0].get('part_number'):
                        pn_list.append(data[0].get('part_number').lower())

                        if query.lower() in pn_list:
                            # Mark data processing as finished
                            await self.update_task_status(task.id, 'mark_data_finished', session=session)
                            
                            # Write to Supabase
                            result = await self.write_to_supabase(data)
                            
                            # Mark Supabase write as finished
                            await self.update_task_status(task.id, 'mark_supabase_finished', session=session)
                            
                            # Mark task as completed
                            await self.update_task_status(task.id, 'mark_completed', session=session)
                            
                            print(f"Written DigiKey data to Supabase for query: {query}")
                            return result
                        else:
                            error_msg = f"Part number: {query} not found in DigiKey results in {pn_list}"
                            print(f"!!! {error_msg}")
                            await self.update_task_status(task.id, 'mark_failed', error_msg, session=session)
                            return {"status": "error", "message": error_msg}
                else:
                    error_msg = f"No data found for query: {query}"
                    await self.update_task_status(task.id, 'mark_failed', error_msg, session=session)
                    return {"status": "error", "message": error_msg}
                            
            except Exception as e:
                error_msg = f"Error processing query {query}: {str(e)}"
                print(f"Error in test_digikey_search: {error_msg}")
                if task:
                    await self.update_task_status(task.id, 'mark_failed', error_msg, session=session)
                return {"status": "error", "message": error_msg}

    async def write_to_supabase(self, data):
        """
        Async write processed data to Supabase PostgreSQL database using async repository classes.
        This method uses async database operations to avoid connection issues.

        Args:
            data: The data to write to Supabase.
        """
        async_engine = get_supabase_async_engine()
        AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)

        async with AsyncSessionLocal() as session:
            try:
                print(f"Starting Supabase async write operation with data length: {len(data)}")

                # Check if data is a dictionary with status information instead of a list of products
                if isinstance(data, dict) and 'status' in data and 'message' in data:
                    print(f"Received status message instead of product data: {data['status']} - {data['message']}")
                    return {"status": "pending", "message": f"Snapshot building: {data['message']}"}

                # Use async repositories
                product_repo = ProductRepository(session)
                manufacturer_repo = ManufacturerRepository(session)
                part_number_repo = PartNumberRepository(session)
                doc_media_repo = DocumentMediaRepository(session)
                attr_repo = ProductAttributeRepository(session)
                extra_repo = ProductExtraRepository(session)
                seller_repo = ProductSellerRepository(session)

                results = []
                for item in data:
                    if not isinstance(item, dict):
                        print(f"Skipping item: {item} - Not a dictionary")
                        continue

                    # Process manufacturer
                    manufacturer_name = item.get('manufacturer', '')
                    existing_manufacturers = await manufacturer_repo.list(name=manufacturer_name)
                    manufacturer = existing_manufacturers[0] if existing_manufacturers else None

                    if not manufacturer:
                        manufacturer = Manufacturer(name=manufacturer_name)
                        session.add(manufacturer)
                        await session.flush()
                        await session.commit()
                    elif manufacturer.manufacturer_id != manufacturer.id:
                        normalized_manufacturer = await session.scalar(
                            select(Manufacturer).where(Manufacturer.id == manufacturer.manufacturer_id)
                        )
                        if normalized_manufacturer:
                            manufacturer = normalized_manufacturer

                    # Process part number
                    part_number_name = item.get('part_number', '')
                    existing_part_numbers = await part_number_repo.list(name=part_number_name)
                    part_number = existing_part_numbers[0] if existing_part_numbers else None

                    if not part_number:
                        part_number = PartNumber(name=part_number_name)
                        session.add(part_number)
                        await session.flush()
                        await session.commit()
                    elif part_number.product_id != part_number.id:
                        normalized_partnumber = await session.scalar(
                            select(PartNumber).where(PartNumber.id == PartNumber.product_id)
                        )
                        if normalized_partnumber:
                            part_number = normalized_partnumber

                    # Process product
                    product = await session.scalar(
                        select(Product).where(
                            and_(
                                Product.part_number == (part_number.product_id if part_number and part_number.product_id == part_number.id else (part_number.product_id if part_number else 0)),
                                Product.manufacturer_id == (manufacturer.manufacturer_id if manufacturer and manufacturer.manufacturer_id == manufacturer.id else (manufacturer.manufacturer_id if manufacturer else 0))
                            )
                        )
                    )
                    if not product:
                        product = Product(
                            part_number=part_number.product_id if part_number and part_number.product_id == part_number.id else (part_number.product_id if part_number else 0),
                            manufacturer_id=manufacturer.manufacturer_id if manufacturer and manufacturer.manufacturer_id == manufacturer.id else (manufacturer.manufacturer_id if manufacturer else 0)
                        )
                        session.add(product)
                        await session.flush()
                        await session.commit()
                    results.append(product)

                    # Process product attributes
                    if 'product_attributes' in item:
                        for attr in item['product_attributes']:
                            attr_type = attr.get('type', 'Unknown')
                            attr_desc = attr.get('description', '')

                            if not attr_desc:
                                print(f"Skipping product attribute with empty description for type: {attr_type}")
                                continue

                            category = await self.get_mp_category(item.get('categories'), session)

                            if hasattr(product, 'category_id'):
                                product.category_id = category.id if category else None
                                session.add(product)
                                await session.flush()
                                await session.commit()

                            attribute = await session.scalar(
                                select(Attribute).where(Attribute.name == attr_type)
                            )
                            if not attribute:
                                attribute = Attribute(name=attr_type)
                                session.add(attribute)
                                await session.flush()

                            if category and attribute:
                                cat_attr = await session.scalar(
                                    select(CategoryAttribute).where(
                                        CategoryAttribute.category_id == category.id,
                                        CategoryAttribute.attribute_id == attribute.id
                                    )
                                )
                                if not cat_attr:
                                    cat_attr = CategoryAttribute(
                                        category_id=category.id,
                                        attribute_id=attribute.id
                                    )
                                    session.add(cat_attr)
                                    await session.commit()

                            if attribute:
                                print(f"Processing product attribute: type={attr_type}, product_id={product.product_id if hasattr(product, 'product_id') else 0}, attribute_id={attribute.id}")
                                attr_obj = ProductAttribute(
                                    product_id=product.product_id if hasattr(product, 'product_id') else 0,
                                    attribute_id=attribute.id,
                                    value_text=attr_desc,
                                    source=self.source,
                                    automation_task_id=self.ref_id
                                )
                                session.add(attr_obj)
                            else:
                                print(f"Skipping product attribute for product_id {product.product_id if hasattr(product, 'product_id') else 0} due to missing attribute")
                        await session.commit()

                    # Process documents and media
                    if 'documents_and_media' in item:
                        for doc in item['documents_and_media']:
                            doc_url = doc.get('link', '')
                            if isinstance(doc_url, (list, set)) and len(doc_url) <= 1:
                                doc_url = next(iter(doc_url), None)
                            if not doc_url:
                                print(f"Skipping document/media with empty URL")
                                continue
                            doc_obj = DocumentMedia(
                                product_id=product.product_id if hasattr(product, 'product_id') else 0,
                                url=doc_url,
                                type=doc.get('type', ''),
                                source=self.source,
                                automation_task_id=self.ref_id
                            )
                            session.add(doc_obj)
                        await session.commit()

                    # Process extra fields
                    excluded_keys = ['part_number', 'manufacturer', 'product_attributes', 'documents_and_media']
                    for key, value in item.items():
                        if key not in excluded_keys and value not in [None, '', [], {}, ()]:
                            extra = ProductExtra(
                                product_id=product.product_id,
                                name=key,
                                value=str(value),
                                source=self.source,
                                automation_task_id=self.ref_id
                            )
                            session.add(extra)
                    await session.commit()

                    # Process sellers if present
                    if 'sellers' in item:
                        for seller in item['sellers']:
                            seller_name = seller.get('seller_name', '')
                            if not seller_name:
                                print(f"Skipping seller with empty seller_name")
                                continue
                            pseller = ProductSeller(
                                product_id=product.product_id if hasattr(product, 'product_id') else 0,
                                seller_name=seller_name,
                                seller_type=seller.get('seller_type', ''),
                                source=self.source,
                                ref_id=self.ref_id
                            )
                            session.add(pseller)
                        await session.commit()

                print(f"Successfully wrote data to Supabase for {len(results)} products")
                return {"status": "success", "message": f"Data written to Supabase for {len(results)} products"}

            except Exception as e:
                print(f"Error in async write_to_supabase: {e}")
                return {"status": "error", "message": "Failed to write data to Supabase due to network issues or other errors."}

    async def write_bq_to_supabase(self, item):
        """
        Async write processed data from BigQuery to Supabase PostgreSQL database using async repository classes.

        Args:
            item: The data item to write to Supabase.
        """
        async_engine = get_supabase_async_engine()
        AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)

        async with AsyncSessionLocal() as session:
            try:
                print("Starting async write_bq_to_supabase operation")

                product_repo = ProductRepository(session)
                manufacturer_repo = ManufacturerRepository(session)
                part_number_repo = PartNumberRepository(session)
                doc_media_repo = DocumentMediaRepository(session)
                attr_repo = ProductAttributeRepository(session)
                extra_repo = ProductExtraRepository(session)
                seller_repo = ProductSellerRepository(session)

                if not isinstance(item, dict):
                    return {"status": "error", "message": f"Skipping item: {item} - Not a dictionary"}

                # Process manufacturer
                manufacturer_name = item.get('manufacturer', '')
                existing_manufacturers = await manufacturer_repo.list(name=manufacturer_name)
                manufacturer = existing_manufacturers[0] if existing_manufacturers else None

                if not manufacturer:
                    manufacturer = Manufacturer(name=manufacturer_name)
                    session.add(manufacturer)
                    await session.flush()
                    await session.commit()
                elif manufacturer.manufacturer_id != manufacturer.id:
                    normalized_manufacturer = await session.scalar(
                        select(Manufacturer).where(Manufacturer.id == manufacturer.manufacturer_id)
                    )
                    if normalized_manufacturer:
                        manufacturer = normalized_manufacturer

                # Process part number
                part_number_name = item.get('pn', '')
                existing_part_numbers = await part_number_repo.list(name=part_number_name)
                part_number = existing_part_numbers[0] if existing_part_numbers else None

                if not part_number:
                    part_number = PartNumber(name=part_number_name)
                    session.add(part_number)
                    await session.flush()
                    await session.commit()
                elif part_number.product_id != part_number.id:
                    normalized_partnumber = await session.scalar(
                        select(PartNumber).where(PartNumber.id == PartNumber.product_id)
                    )
                    if normalized_partnumber:
                        part_number = normalized_partnumber

                # Process product
                product = await session.scalar(
                    select(Product).where(
                        and_(
                            Product.part_number == (part_number.product_id if part_number and part_number.product_id == part_number.id else (part_number.product_id if part_number else 0)),
                            Product.manufacturer_id == (manufacturer.manufacturer_id if manufacturer and manufacturer.manufacturer_id == manufacturer.id else (manufacturer.manufacturer_id if manufacturer else 0))
                        )
                    )
                )
                if not product:
                    product = Product(
                        part_number=part_number.product_id if part_number and part_number.product_id == part_number.id else (part_number.product_id if part_number else 0),
                        manufacturer_id=manufacturer.manufacturer_id if manufacturer and manufacturer.manufacturer_id == manufacturer.id else (manufacturer.manufacturer_id if manufacturer else 0)
                    )
                    session.add(product)
                    await session.flush()
                    await session.commit()

                # Create or fetch Category
                category_names = item.get('category')
                if category_names:
                    category_names = category_names.split(' -> ')

                category = await self.get_mp_category(item.get('categories'), session)


                if hasattr(product, 'category_id'):
                    product.category_id = category.id if category else None
                    session.add(product)
                    await session.flush()
                    await session.commit()

                # Process specs
                if 'specs' in item and isinstance(item['specs'], np.ndarray) and item['specs'].size > 0:
                    for attr in item['specs']:
                        attr_type = attr.get('spec_name')

                        if not attr_type:
                            print(f"Skipping attribute due to missing spec_name in item: {attr}")
                            continue

                        if not attr.get('spec_value'):
                            print(f"Skipping spec attribute with empty spec_value for spec_name: {attr_type}")
                            continue

                        attribute = await session.scalar(
                            select(Attribute).where(Attribute.name == attr_type)
                        )
                        if not attribute:
                            attribute = Attribute(name=attr_type)
                            session.add(attribute)
                            await session.flush()

                        category = product.category if hasattr(product, 'category') else None
                        if category and attribute:
                            cat_attr = await session.scalar(
                                select(CategoryAttribute).where(
                                    CategoryAttribute.category_id == category.id,
                                    CategoryAttribute.attribute_id == attribute.id
                                )
                            )
                            if not cat_attr:
                                cat_attr = CategoryAttribute(
                                    category_id=category.id,
                                    attribute_id=attribute.id
                                )
                                session.add(cat_attr)
                                await session.commit()

                        if attribute:
                            print(f"Processing product attribute: type={attr_type}, product_id={product.product_id if hasattr(product, 'product_id') else 0}, attribute_id={attribute.id}")
                            attr_obj = ProductAttribute(
                                product_id=product.product_id if hasattr(product, 'product_id') else 0,
                                attribute_id=attribute.id,
                                value_text=attr.get('spec_value', ''),
                                value_unit=attr.get('spec_units', ''),
                                source=self.source,
                                automation_task_id=self.ref_id if self.ref_id > 0 else None
                            )
                            session.add(attr_obj)
                            print(f"Added product attribute for product_id {product.product_id if hasattr(product, 'product_id') else 0} with type: {attr_type} and attribute_id: {attribute.id}")
                        else:
                            print(f"Skipping product attribute for product_id {product.product_id if hasattr(product, 'product_id') else 0} due to missing attribute")
                    await session.commit()

                # Process docs
                if 'docs' in item:
                    for doc in item['docs']:
                        doc_url = doc.get('doc_url', '')
                        if isinstance(doc_url, (list, set)) and len(doc_url) <= 1:
                            doc_url = next(iter(doc_url), None)
                        if not doc_url:
                            print(f"Skipping doc with empty URL")
                            continue
                        doc_obj = DocumentMedia(
                            product_id=product.product_id if hasattr(product, 'product_id') else 0,
                            url=doc_url,
                            type=doc.get('doc_type', ''),
                            description=doc.get('doc_desc', ''),
                            source=self.source,
                            automation_task_id=self.ref_id if self.ref_id > 0 else None
                        )
                        session.add(doc_obj)
                    await session.commit()

                # Process images
                if 'images' in item:
                    for doc in item['images']:
                        doc_url = doc.get('image_url', '')
                        if isinstance(doc_url, (list, set)) and len(doc_url) <= 1:
                            doc_url = next(iter(doc_url), None)
                        if not doc_url:
                            print(f"Skipping image with empty URL")
                            continue
                        doc_obj = DocumentMedia(
                            product_id=product.product_id if hasattr(product, 'product_id') else 0,
                            url=doc_url,
                            type='image',
                            source=self.source,
                            automation_task_id=self.ref_id if self.ref_id > 0 else None
                        )
                        session.add(doc_obj)
                    await session.commit()

                # Process compliance
                if 'compliance' in item:
                    for ext in item['compliance']:
                        val = ext.get('value', '')
                        if val in [None, '']:
                            print(f"Skipping compliance extra with empty value")
                            continue
                        extra = ProductExtra(
                            product_id=product.product_id if hasattr(product, 'product_id') else 0,
                            name=ext.get('type', ''),
                            value=str(val),
                            source=self.source,
                            automation_task_id=self.ref_id if self.ref_id > 0 else None
                        )
                        session.add(extra)
                    await session.commit()

                # Process extra
                if 'extra' in item:
                    for ext in item['extra']:
                        val = ext.get('value', '')
                        if val in [None, '']:
                            print(f"Skipping extra with empty value")
                            continue
                        extra = ProductExtra(
                            product_id=product.product_id if hasattr(product, 'product_id') else 0,
                            name=ext.get('name', ''),
                            value=str(val),
                            source=self.source,
                            automation_task_id=self.ref_id if self.ref_id > 0 else None
                        )
                        session.add(extra)
                    await session.commit()

                # Process sellers
                if 'sellers' in item:
                    for seller in item['sellers']:
                        seller_name = seller.get('seller_name', '')
                        if not seller_name:
                            print(f"Skipping seller with empty seller_name")
                            continue
                        pseller = ProductSeller(
                            product_id=product.product_id if hasattr(product, 'product_id') else 0,
                            seller_name=seller_name,
                            seller_type=seller.get('seller_type', ''),
                            source=self.source,
                            ref_id=self.ref_id
                        )
                        session.add(pseller)
                    await session.commit()

                # Process specific keys as extras
                for key in  ['product_id', 'category', 'description', 'intro_date', 'country_of_origin', 'active_for_use', 
                             'manuf_standard_packaging', 'product_series', 'brand', 'title', 'lifecycle_status', 'package_type']:
                    if key in item and item[key] not in [None, '', [], {}, ()]:
                        extra = ProductExtra(
                            product_id=product.product_id if hasattr(product, 'product_id') else 0,
                            name= key,
                            value=str(item[key]),
                            source=self.source,
                            automation_task_id=self.ref_id if self.ref_id > 0 else None
                        )
                        session.add(extra)
                await session.commit()

                print("Successfully wrote BigQuery data to Supabase")
                return {"status": "success", "message": "BigQuery data written to Supabase"}

            except Exception as e:
                print(f"Error in async write_bq_to_supabase: {e}")
                return {"status": "error", "message": "Failed to write BigQuery data to Supabase due to network issues or other errors."}

# Setup file logger for progress tracking
def setup_progress_logger():
    """Setup a file logger for progress tracking."""
    logger = logging.getLogger('automation_progress')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler
    file_handler = logging.FileHandler('automation_progress.log')
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(file_handler)
    
    return logger

# Global progress logger
progress_logger = setup_progress_logger()

async def process_single_pn(pn: str, ss, processed_count: list, total_count: int, batch_id: str = None, retry_count: int = 3):
    """
    Process a single part number asynchronously with retry logic and AutomationTask tracking.
    
    Args:
        pn: Part number to process
        ss: DataFrame containing the data
        processed_count: List containing current processed count (mutable reference)
        total_count: Total number of PNs to process
        batch_id: Batch identifier for tracking related tasks
        retry_count: Number of retries for failed operations (default: 3)
    """
    for attempt in range(retry_count):
        try:
            automator = TaskAutomator()
            item = ss[ss['pn'] == pn]
            
            if item.shape[0] > 0:
                item = item.iloc[0].to_dict()
                await automator.write_bq_to_supabase(item)
            
            # Use the enhanced test_digikey_search with automation task tracking
            await automator.test_digikey_search(pn, batch_id)
            
            # Update progress counter on success
            processed_count[0] += 1
            progress_msg = f"✅ Progress: {processed_count[0]}/{total_count} - PN: {pn} completed successfully."
            progress_logger.info(progress_msg)
            return  # Success, exit retry loop
            
        except Exception as e:
            if attempt < retry_count - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                error_msg = f"⚠️  Error processing PN {pn} (attempt {attempt + 1}): {str(e)}. Retrying in {wait_time}s..."
                progress_logger.warning(error_msg)
                await asyncio.sleep(wait_time)
            else:
                processed_count[0] += 1
                final_error_msg = f"❌ Progress: {processed_count[0]}/{total_count} - Failed to process PN {pn} after {retry_count} attempts: {str(e)}"
                progress_logger.error(final_error_msg)

async def progress_reporter(processed_count: list, total_count: int, start_time: float):
    """
    Periodically report progress statistics to log file.
    
    Args:
        processed_count: List containing current processed count
        total_count: Total number of items to process
        start_time: Start time of the process
    """
    while processed_count[0] < total_count:
        await asyncio.sleep(30)  # Report every 30 seconds
        elapsed_time = time.time() - start_time
        rate = processed_count[0] / elapsed_time if elapsed_time > 0 else 0
        remaining = total_count - processed_count[0]
        eta = remaining / rate if rate > 0 else 0
        
        progress_msg = f"📊 Progress Report: {processed_count[0]}/{total_count} ({processed_count[0]/total_count*100:.1f}%) | Rate: {rate:.2f} PNs/sec | ETA: {eta/60:.1f} min"
        progress_logger.info(progress_msg)

async def get_bq_wr_supabase_async(max_concurrent: int = 3):
    """
    Async version of get_bq_wr_supabase with parallel processing, progress tracking, and AutomationTask management.
    
    Args:
        max_concurrent: Maximum number of concurrent tasks to run (default: 10)
    """
    from src.db.services.bigquery_service import fetch_all_data_sorted
    
    start_time = time.time()
    
    # Generate batch ID for this processing run
    batch_id = f"batch_{int(start_time)}"
    
    # Log start to file
    progress_logger.info("🔄 Fetching data from BigQuery...")
    ss = fetch_all_data_sorted(limit=2100) 
    pns = ss.iloc[2000:]['pn'].unique()
    total_count = len(pns)
    
    start_msg = f"🚀 START: {total_count} part numbers to process with max {max_concurrent} concurrent tasks (Batch: {batch_id})"
    progress_logger.info(start_msg)
    
    # Use a list to track processed count (mutable reference for async tasks)
    processed_count = [0]
    
    # Create semaphore to limit concurrent tasks
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(pn):
        async with semaphore:
            await process_single_pn(pn, ss, processed_count, total_count, batch_id)
    
    # Create tasks for all PNs
    tasks = [process_with_semaphore(pn) for pn in pns]
    
    # Start progress reporter
    progress_task = asyncio.create_task(progress_reporter(processed_count, total_count, start_time))
    
    # Log processing start
    progress_logger.info("⚡ Starting parallel processing...")
    
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        progress_task.cancel()  # Stop progress reporter
    
    elapsed_time = time.time() - start_time
    avg_rate = processed_count[0] / elapsed_time if elapsed_time > 0 else 0
    
    completion_msg = f"🎉 All tasks completed! Processed {processed_count[0]}/{total_count} part numbers in {elapsed_time/60:.1f} minutes (Batch: {batch_id})"
    rate_msg = f"📈 Average processing rate: {avg_rate:.2f} PNs/second"
    
    progress_logger.info(completion_msg)
    progress_logger.info(rate_msg)

def get_bq_wr_supabase():
    """
    Synchronous wrapper for the async function to maintain backward compatibility.
    """
    asyncio.run(get_bq_wr_supabase_async())

if __name__ == "__main__":
    import sys
    
    # Check if user wants to specify max concurrent tasks
    max_concurrent = 10  # default
    if len(sys.argv) > 1:
        try:
            max_concurrent = int(sys.argv[1])
            progress_logger.info(f"Using max concurrent tasks: {max_concurrent}")
        except ValueError:
            progress_logger.warning(f"Invalid concurrent tasks argument: {sys.argv[1]}, using default: {max_concurrent}")
    
    # Run the async version directly for better performance
    asyncio.run(get_bq_wr_supabase_async(max_concurrent))
