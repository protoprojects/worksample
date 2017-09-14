from rest_framework import permissions


class IsMortgageProfileOwner(permissions.AllowAny):

    def has_permission(self, request, view):
        """
        Check if mortgage profile is present in session.

        """
        return request.session.get('mortgage_profile_uuid', False)

    def has_object_permission(self, request, view, obj):
        """
        Check if current user own current mortgage profile.

        """
        return request.session.get('mortgage_profile_uuid', -1) == obj.uuid


class HasNoLoanProfile(permissions.BasePermission):
    message = 'this mortgage_profile is already references a loan_profile'

    def has_object_permission(self, request, view, obj):
        """
        Check if the current mortgage_profile has a loan_profile associated with it.
        if there is a loan_profile, disallow the action.  The mortgage_profile in the session
        should never be used to update a mortgage_profile that is associated with a registered user.
        """
        has_loan_profile = obj.loan_profilev1 is not None
        if has_loan_profile:
            # if the mortgage_profile already has a loan_profile we want to remove
            # the mortgage_profile.uuid from the session so that the client cannot update it.
            # Within the consumer_portal, there are separate endpoints for updating the mortgage_profile
            # that do not rely on the session
            request.session.clear()
            return False
        return True
