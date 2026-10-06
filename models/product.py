from services.product_service import ProductService

class ProductModel:
    @classmethod
    def find_all(cls, filter_query=None, sort_field='created_at', sort_order=-1, page=1, limit=12, active_only=True, only_deleted=False, only_staging=False):
        s_order = 'desc' if sort_order in (-1, 'desc', 'DESC') else 'asc'
        return ProductService.get_all(
            filter_query=filter_query, 
            sort_field=sort_field, 
            sort_order=s_order, 
            page=page, 
            limit=limit, 
            active_only=active_only,
            only_deleted=only_deleted,
            only_staging=only_staging
        )

    @classmethod
    def find_by_slug(cls, subcategory_slug, product_slug):
        return ProductService.get_by_slug(subcategory_slug, product_slug)

    @classmethod
    def find_by_id(cls, product_id, include_deleted=False):
        return ProductService.get_by_id(product_id, include_deleted=include_deleted)

    @classmethod
    def find_featured(cls, limit=8):
        return ProductService.get_featured(limit=limit)

    @classmethod
    def create(cls, data):
        return ProductService.create(data)

    @classmethod
    def update(cls, product_id, data):
        return ProductService.update(product_id, data)

    @classmethod
    def delete(cls, product_id):
        return ProductService.delete(product_id)

    @classmethod
    def restore(cls, product_id):
        return ProductService.restore(product_id)

    @classmethod
    def permanent_delete(cls, product_id):
        return ProductService.permanent_delete(product_id)

    @classmethod
    def empty_recycle_bin(cls):
        return ProductService.empty_recycle_bin()

    @classmethod
    def get_recycle_bin_count(cls):
        return ProductService.get_recycle_bin_count()

    @classmethod
    def get_staging_count(cls):
        return ProductService.get_staging_count()

    @classmethod
    def move_category_products_to_staging(cls, category_slug):
        return ProductService.move_category_products_to_staging(category_slug)

    @classmethod
    def reorder(cls, order_list):
        return ProductService.reorder(order_list)
