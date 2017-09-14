from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class AccountsBackend(ModelBackend):
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            # pylint: disable=protected-access
            return UserModel._default_manager.get_subclass(pk=user_id)
        except UserModel.DoesNotExist:
            return None
