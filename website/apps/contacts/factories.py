import factory as factory_boy

from contacts.models import (
    ContactRequestMortgageProfile, ContactRequestAboutUs,
    ContactRequestLandingExtended,
    ConsultationRequest, Location,
)


class ContactRequestMortgageProfileFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = ContactRequestMortgageProfile


class ContactRequestAboutUsFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = ContactRequestAboutUs


class ContactRequestLandingExtendedFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = ContactRequestLandingExtended


class ConsultationRequestFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = ConsultationRequest


class LocationFactory(factory_boy.DjangoModelFactory):
    class Meta:
        model = Location
