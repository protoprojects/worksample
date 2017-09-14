from rest_framework.permissions import BasePermission


class IsMobileProfileOwner(BasePermission):

    def has_permission(self, request, view):
        """
        Check if mobile profile is present in session.

        """
        return request.session.get('mobile_profile_id', False)

    def has_object_permission(self, request, view, obj):
        """
        Check if current user owns current mobile profile.

        """
        return request.session.get('mobile_profile_id', -1) == obj.id
