from services.category_service import CategoryService, SubcategoryService

class CategoryModel:
    @classmethod
    def find_all(cls, business_slug=None):
        return CategoryService.get_all(business_slug=business_slug)

    @classmethod
    def find_by_slug(cls, slug):
        return CategoryService.get_by_slug(slug)

    @classmethod
    def create(cls, data):
        return CategoryService.create(data)

    @classmethod
    def delete(cls, category_slug):
        return CategoryService.delete(category_slug)

class SubcategoryModel:
    @classmethod
    def find_by_category(cls, category_id):
        return SubcategoryService.get_by_category(category_id)

    @classmethod
    def find_all(cls):
        return SubcategoryService.get_all()

    @classmethod
    def create(cls, data):
        return SubcategoryService.create(data)

    @classmethod
    def delete(cls, subcategory_slug):
        return SubcategoryService.delete(subcategory_slug)
