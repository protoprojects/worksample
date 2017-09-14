from rest_framework import permissions


class IsLoanOwnerPermission(permissions.IsAuthenticatedOrReadOnly):
    def has_object_permission(self, request, view, loan):
        """
        Check if authenticated user is owner of current loan.

        """
        return loan.customer == request.user
