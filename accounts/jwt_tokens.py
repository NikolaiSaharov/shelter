from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

class CustomRefreshToken(RefreshToken):
    @classmethod
    def for_user(cls, user):
        token = cls()
        token['user_id'] = user.user_id
        token['email'] = user.email
        return token

