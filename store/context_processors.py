from organizations.models import Organization

def organizations_processor(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return {
            "all_organizations": Organization.objects.all(),
            "selected_org_id": request.session.get("selected_org_id"),
        }
    return {}