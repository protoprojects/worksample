from accounts.models import Customer


class ContactRequestMiddleware(object):
    @staticmethod
    def process_request(request):
        if not request.session.get("account_number"):
            request.session["account_number"] = Customer.objects.generate_account_number()
