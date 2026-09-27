from services.enquiry_service import EnquiryService

class EnquiryModel:
    @classmethod
    def create(cls, data):
        return EnquiryService.create(data)

    @classmethod
    def find_all(cls, status=None, view='active', search=None, page=1, limit=20):
        return EnquiryService.get_all(status=status, view=view, search=search, page=page, limit=limit)

    @classmethod
    def get_by_id(cls, enquiry_id):
        return EnquiryService.get_by_id(enquiry_id)

    @classmethod
    def update_status(cls, enquiry_id, status, notes=None):
        return EnquiryService.update_status(enquiry_id, status, notes=notes)

    @classmethod
    def soft_delete(cls, enquiry_id):
        return EnquiryService.soft_delete(enquiry_id)

    @classmethod
    def restore(cls, enquiry_id):
        return EnquiryService.restore(enquiry_id)

    @classmethod
    def permanent_delete(cls, enquiry_id):
        return EnquiryService.permanent_delete(enquiry_id)

    @classmethod
    def empty_recycle_bin(cls):
        return EnquiryService.empty_recycle_bin()

    @classmethod
    def get_recycle_bin_count(cls):
        return EnquiryService.get_recycle_bin_count()

    @classmethod
    def get_stats(cls):
        return EnquiryService.get_stats()

