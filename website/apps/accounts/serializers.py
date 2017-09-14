from rest_framework import serializers

from accounts.models import User, Customer, Address


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ('id', 'first_name', 'last_name', 'email', 'phone',)


class CustomerSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            'transactional_emails_subscribed', 'lifecycle_emails_subscribed',
            'marketing_emails_subscribed', 'surveys_reminders_subscribed',)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = '__all__'
        read_only_fields = ('customer',)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name',)
