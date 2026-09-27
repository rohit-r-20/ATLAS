from services.brand_service import BrandService

class BrandModel:
    @classmethod
    def find_all(cls, featured_only=False, business_slug=None, search=None, is_active_only=True):
        return BrandService.get_all(featured_only=featured_only, business_slug=business_slug, search=search, is_active_only=is_active_only)

    @classmethod
    def find_by_slug(cls, slug):
        return BrandService.get_by_slug(slug)

    @classmethod
    def find_by_id(cls, brand_id):
        return BrandService.get_by_id(brand_id)

    @classmethod
    def create(cls, data):
        return BrandService.create(data)

    @classmethod
    def update(cls, brand_id_or_slug, data):
        return BrandService.update(brand_id_or_slug, data)

    @classmethod
    def delete(cls, brand_id_or_slug):
        return BrandService.delete(brand_id_or_slug)
