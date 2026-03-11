from django.http import HttpResponse
from store.utils import get_user_organization

class OrganizationStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            org = get_user_organization(request)
            if not org.is_active:
                return HttpResponse("Your organization subscription is inactive.")

        return self.get_response(request)
