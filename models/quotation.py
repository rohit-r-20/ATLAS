from services.quotation_service import QuotationService

class QuotationModel:
    @classmethod
    def create(cls, data):
        return QuotationService.create_quotation(data)

    @classmethod
    def find_all(cls, status=None, search=None, page=1, limit=20):
        return QuotationService.get_all(status=status, search=search, page=page, limit=limit)

    @classmethod
    def find_by_id(cls, quote_id):
        return QuotationService.get_by_id(quote_id)

    @classmethod
    def update(cls, quote_id, data):
        return QuotationService.update_quotation(quote_id, data)

    @classmethod
    def update_quotation(cls, quote_id, data):
        return QuotationService.update_quotation(quote_id, data)

    @classmethod
    def update_status(cls, quote_id, status, notes=None):
        return QuotationService.update_status(quote_id, status, notes=notes)

    @classmethod
    def delete(cls, quote_id):
        return QuotationService.delete(quote_id)

    @classmethod
    def get_stats(cls):
        return QuotationService.get_stats()
