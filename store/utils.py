from organizations.models import Organization

def get_user_organization(request):
    # Superuser: allow session-based switching
    if request.user.is_superuser:
        org_id = request.session.get("selected_org_id")
        if org_id:
            return Organization.objects.get(id=org_id)
        return Organization.objects.first()  # default fallback
    
    # Normal users
    if hasattr(request.user, "userprofile"):
        return request.user.userprofile.organization
    
    return None