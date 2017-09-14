# -*- coding: utf-8 -*-
from rest_framework import serializers

from accounts.models import Customer
from core.fields import NativeField


class AdvisorCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ('id', 'first_name', 'last_name', 'email', 'phone',)
        read_only_fields = ('advisor',)
