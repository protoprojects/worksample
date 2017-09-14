from rest_framework import permissions


INSTANCE_COUNT_MAXIMUM_DEFAULT = 20


class InstanceCountMaximumPermission(permissions.BasePermission):
    create_methods = ['POST']

    # Override in the view
    instance_count_maximum = INSTANCE_COUNT_MAXIMUM_DEFAULT

    def has_permission(self, request, view):
        if request.method in self.create_methods:
            count_max = getattr(view, 'instance_count_maximum', self.instance_count_maximum)
            return view.get_queryset().count() < count_max
        return True
