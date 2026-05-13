from .models import User, UserProfile
from .utils import get_user_from_jwt

def auth_user(request):
    u = get_user_from_jwt(request)
    data = None
    if u:
        try:
            prof = UserProfile.objects.get(user=u)
            avatar = prof.profile_picture or ''
        except UserProfile.DoesNotExist:
            avatar = ''
        initial = (u.first_name[:1] if u.first_name else u.email[:1]).upper()
        data = {
            'id': u.user_id,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'email': u.email,
            'avatar_url': avatar,
            'initial': initial,
            'full_name': f"{u.first_name} {u.last_name}".strip(),
            'role': u.role.role_name if u.role else None,
        }
    return { 'auth_user': data }
