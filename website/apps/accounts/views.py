import logging

from twilio import twiml
from authtools.views import (
    PasswordChangeView as AuthtoolsPasswordChangeView,
    LoginView as AuthtoolsLoginView,
    LogoutView)
from braces.views import LoginRequiredMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.core import signing
from django.conf import settings
from django.http import Http404, HttpResponse
from django.views.generic.edit import FormView, UpdateView
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from pinax.notifications import models as notification
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework_jwt.authentication import JSONWebTokenAuthentication

from customer_portal.permissions import IsAuthenticatedCustomer
from pages.views import IndexView

from accounts.authentication_mixins import WebTokenAuthenticationMixin
from accounts.forms import CustomerSettingsForm, RegistrationForm
from accounts.models import Address, Customer, CustomerEmailValidation, PhoneVerification
from accounts.permissions import DenyAllPermission, TwilioCallbackPermission
from accounts.serializers import (
    AddressSerializer, CustomerSerializer, CustomerSubscriptionSerializer)
from customer_portal.serializers import CustomerPasswordChangeSerializer, CustomerProfileSerializer

logger = logging.getLogger('sample.accounts.views')


class CustomerSettingsView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerSettingsForm
    template_name = "accounts/settings.html"

    # pylint: disable=redefined-builtin
    def get_object(self, format=None):
        return self.request.user

    def get_success_url(self):
        return reverse('user_settings')

customer_settings_view = CustomerSettingsView.as_view()


class RegistrationView(FormView):
    form_class = RegistrationForm
    template_name = 'registration/registration_form.html'

    def get_success_url(self):
        return reverse('user_settings')

    def form_valid(self, form):
        self.register(self.request, **form.cleaned_data)
        return redirect(self.get_success_url())

    @classmethod
    def register(cls, request, **cleaned_data):
        email, password = cleaned_data['email'], cleaned_data['password1']

        Customer.objects.create_user(email, password, name=cleaned_data['name'])
        new_user = authenticate(username=email, password=password)

        notification.send([new_user], "registration_new_user")

        login(request, new_user)
        return new_user

registration_view = RegistrationView.as_view()


# pylint: disable=inconsistent-mro
# Disabled since pylint error was brought by parent class from django-authtools.
class PasswordChangeView(AuthtoolsPasswordChangeView):
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        notification.send([self.request.user], "registration_password_change")
        return super(PasswordChangeView, self).form_valid(form)

password_change = PasswordChangeView.as_view()

logout = LogoutView.as_view(url=reverse_lazy('index'), template_name='registration/logout.html')


class LoginView(AuthtoolsLoginView):
    def form_valid(self, form):
        if not self.request.POST.get('remember_me', None):
            self.request.session.set_expiry(0)
        login(self.request, form.get_user())
        return super(LoginView, self).form_valid(form)

login_view = LoginView.as_view()


class ApiLoginView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    @method_decorator(ensure_csrf_cookie)
    def post(self, request, *args, **kwargs):
        email = self.request.data.get('email')
        password = self.request.data.get('password')
        if email and password:
            user = authenticate(username=email, password=password)

            if user is None:
                return Response(
                    {'invalid_login': "Please enter a correct email and password."},
                    status=status.HTTP_400_BAD_REQUEST)

            login(self.request, user)
            return Response({}, status=status.HTTP_200_OK)

        else:
            return Response({'invalid_login': "Something goes wrong."}, status=status.HTTP_400_BAD_REQUEST)

api_login_view = ApiLoginView.as_view()


class EncompassUserView(generics.ListCreateAPIView):
    model = Customer
    serializer_class = CustomerSerializer
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)
    filter_fields = ('email', 'phone')

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # pylint: disable=W0612
            user, _password = Customer.objects.create_user_with_random_password(
                serializer.validated_data['email'],
                phone=serializer.validated_data['phone'])
            return Response(self.get_serializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

encompass_user_view = EncompassUserView.as_view()


class EncompassUserDetailsView(generics.RetrieveUpdateAPIView):
    model = Customer
    serializer_class = CustomerSerializer
    permission_classes = (permissions.IsAuthenticated,)
    authentication_classes = (JSONWebTokenAuthentication,)
    lookup_field = 'email'

encompass_user_details = EncompassUserDetailsView.as_view()


class ApiResetPasswordView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    # pylint: disable=redefined-builtin
    def post(self, request, format=None):
        email = self.request.data.get('email')

        if email:
            if not Customer.objects.filter(email=email).exists():
                return Response(
                    {'invalid_email': "User with such email doesn't exist."},
                    status=status.HTTP_400_BAD_REQUEST)

            context = {
                'token': signing.dumps(email, settings.SALT),
                'scheme': 'https' if request.is_secure() else 'http',
                'host': request.get_host()
            }
            notification.send([Customer.objects.get(email=email)], 'reset_password', context)
            return Response({}, status=status.HTTP_200_OK)

        else:
            return Response(
                {'invalid_email': "Email can't be empty."}, status=status.HTTP_400_BAD_REQUEST)

api_reset_password_view = ApiResetPasswordView.as_view()


def _check_token_or_404(token):
    if not token:
        raise Http404

    try:
        email = signing.loads(token, settings.SALT, max_age=settings.RESET_PASSWORD_TOKEN_EXPIRES)
    except signing.SignatureExpired:
        raise Http404

    if not Customer.objects.filter(email=email).exists():
        raise Http404

    return email


class ResetPasswordDoneView(IndexView):
    def dispatch(self, *args, **kwargs):
        _check_token_or_404(kwargs.get('token'))

        return super(ResetPasswordDoneView, self).dispatch(*args, **kwargs)


reset_password_done_view = ResetPasswordDoneView.as_view()


class ApiChangePasswordView(views.APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, *args, **kwargs):
        email = _check_token_or_404(self.kwargs.get('token'))

        new_password = self.request.data.get('password')

        user = Customer.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        return Response({}, status=status.HTTP_200_OK)


api_change_password_view = ApiChangePasswordView.as_view()


class ApiCustomerSettingsView(generics.RetrieveUpdateAPIView):
    """
    Endpoint for managing user settings
    """

    permission_classes = (IsAuthenticatedCustomer,)
    model = Customer
    serializer_class = CustomerProfileSerializer

    def get_object(self):
        return self.request.user.customer

api_customer_settings_view = ApiCustomerSettingsView.as_view()


class ApiUpdatePasswordView(generics.UpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    model = Customer
    serializer_class = CustomerPasswordChangeSerializer

    def get_object(self):
        return self.request.user

api_update_password_view = ApiUpdatePasswordView.as_view()


class ApiCustomerSubscriptionView(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticatedCustomer,)
    model = Customer
    serializer_class = CustomerSubscriptionSerializer

    def get_object(self):
        return self.request.user

api_customer_subscription_view = ApiCustomerSubscriptionView.as_view()


class ApiAddressesView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    model = Address
    serializer_class = AddressSerializer

    def perform_create(self, serializer):
        return serializer.save(customer_id=self.kwargs.get('customer_pk'))

    def get_queryset(self, *args, **kwargs):
        customer = generics.get_object_or_404(Customer,
                                              pk=self.kwargs.get('customer_pk'))
        return customer.addresses.all()

api_customer_addresses = ApiAddressesView.as_view()


class UserProfileView(WebTokenAuthenticationMixin, generics.RetrieveAPIView):
    permission_classes = (DenyAllPermission,)

    # pylint: disable=redefined-builtin
    def get_object(self, format=None):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        if self.request.user.is_authenticated():
            return super(UserProfileView, self).retrieve(request, *args, **kwargs)

        return Response(status=status.HTTP_403_FORBIDDEN)


class BaseEmailVerificationAPIView(views.APIView):
    """
    Base class used to verify or decline user's email address.
    """

    permission_classes = (permissions.AllowAny,)

    def _log_failed(self, cev_code, message):
        logger.info('EMAIL-VERIFICATION-FAILED <%s> %s', cev_code, message)

    def handle_code(self, cev):
        raise NotImplementedError()

    def get(self, request, *args, **kwargs):
        code = request.query_params.get('code')
        if not code:
            msg = "Code hasn't been provided."
            self._log_failed("''", msg)
            return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cev = CustomerEmailValidation.objects.get(code=code)
        except CustomerEmailValidation.DoesNotExist:
            msg = "Code doesn't exist."
            self._log_failed(code, msg)
            return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

        if not cev.is_active:
            msg = 'Code has been deactivated.'
            self._log_failed(code, msg)
            return Response({'detail': msg}, status=status.HTTP_409_CONFLICT)

        if cev.is_redeemed:
            msg = 'Code has already been verified.'
            self._log_failed(code, msg)
            return Response({'detail': msg}, status=status.HTTP_201_CREATED)

        return self.handle_code(cev)


class VerifyEmailCustomerView(BaseEmailVerificationAPIView):
    """
    Verify an email address for customer by unique token.
    """

    def handle_code(self, cev):
        cev.verify()

        customer = cev.customer
        logger.info('CUSTOMER-EMAIL-VERIFIED Customer ID: %s.', customer.id)
        return Response({'detail': 'Code successfully verified.'},
                        status=status.HTTP_200_OK)

verify_email = VerifyEmailCustomerView.as_view()


class DeclineEmailCustomerView(BaseEmailVerificationAPIView):
    """
    Decline an email address for customer by unique token.
    """

    def handle_code(self, cev):
        cev.decline()

        customer = cev.customer
        customer.is_active = False
        customer.save()
        logger.info('CUSTOMER-EMAIL-REPUDIATED Customer ID: %s.', customer.id)
        return Response({'detail': 'Code successfully repudiated.'},
                        status=status.HTTP_200_OK)

decline_email = DeclineEmailCustomerView.as_view()


class PhoneVerificationTwilioCallback(generics.GenericAPIView):
    """
    Response TwiML XML instruction.
    https://www.twilio.com/docs/api/twiml
    TwiML is a set of instructions you can use to tell Twilio what to do when you receive an incoming call or SMS.
    In our case Twilio plays message for the caller with confirmation code.
    """
    permission_classes = (TwilioCallbackPermission,)

    @staticmethod
    def _say_code(r, code):
        for i in code:
            r.pause(length=1)  # wait 1 sec before spelling
            r.say(i)

    def post(self, request, *args, **kwargs):
        verification_code = request.GET.get('verification_code')

        try:
            verification_obj = PhoneVerification.objects.get(code=verification_code, is_verified=False)
        except PhoneVerification.DoesNotExists:
            return Response(status=status.HTTP_204_NO_CONTENT)

        r = twiml.Response()
        r.say('Your verification code is')
        self._say_code(r, verification_obj.code)
        r.pause(length=2)  # wait 2 seconds before repeat
        r.say('Repeat again')
        self._say_code(r, verification_obj.code)
        return HttpResponse(r.toxml())

phone_verification_twilio_callback_view = PhoneVerificationTwilioCallback.as_view()
