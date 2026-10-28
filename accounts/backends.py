from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """Login boleh memakai e-mail atau username (akun staf yang dibuat lewat /admin/)."""
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if not username or password is None:
            return None

        # Satu e-mail bisa saja dipakai dua akun lama, jadi coba semuanya.
        for user in User.objects.filter(Q(username__iexact=username) | Q(email__iexact=username)):
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        User().set_password(password)  # samakan waktu respons
        return None
