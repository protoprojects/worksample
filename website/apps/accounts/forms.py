from django import forms
from django.forms.utils import flatatt
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from suit_redactor.widgets import RedactorWidget
from authtools.forms import AdminUserChangeForm

from accounts.models import Customer


class CustomerSettingsForm(forms.ModelForm):
    """
    Form for updating specific customer information.

    """
    class Meta:
        model = Customer
        fields = ('first_name', 'last_name', 'email', )


class RegistrationForm(forms.Form):
    """
    Form for registering a new user account.

    """
    first_name = forms.CharField(label="First Name")
    last_name = forms.CharField(label="Last Name")
    email = forms.EmailField(label="E-mail")
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Password (again)")

    def clean_email(self):
        """
        Validate that the username is alphanumeric and is not already in use.

        """
        existing = Customer.objects.filter(email__iexact=self.cleaned_data['email'])
        if existing.exists():
            raise forms.ValidationError("A user with that email already exists.")
        else:
            return self.cleaned_data['email']

    def clean(self):
        """
        Verifiy that the values entered into the two password fields match.

        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError("The two password fields didn't match.")

        return self.cleaned_data


class AdminAdvisorForm(AdminUserChangeForm):
    class Meta:
        widgets = {
            'short_biography': RedactorWidget(editor_options={'lang': 'en'})
        }


class JsonCheckboxesWidget(forms.Textarea):
    """
    Handle rendering and converting data for `Customer.contact_preferences`

    """

    def value_from_datadict(self, data, files, name):
        """
        Restore `contact preferences` structure from inputs values

        """

        checkboxes_data = {}
        field_prefix = "%s__" % name

        if data:
            # check input items which starts with `name` + `__`
            # this items are marked `on`, so append it with `True`
            for field_name in data:
                if field_name.startswith(field_prefix):
                    origin_field_name = field_name.replace(field_prefix, '')
                    checkboxes_data[origin_field_name] = True

            # if `data` doesn't contains field from `DEFAULT_CONTACT_PREFERENCES_DICT`
            # that append it with `False` value
            for field_name in Customer.DEFAULT_CONTACT_PREFERENCES_DICT:
                checkboxes_data.setdefault(field_name, False)

        return checkboxes_data

    def render(self, name, value, attrs=None):
        """
        Renders json structure of `Customer.contact_preferences` into list of checkboxes

        """

        checkboxes = []
        field_prefix = "%s__" % name
        html_template = '<div class="control-label">{0}</div> <div class="controls"><input{1} /></div>'

        if not value:
            return ''

        for fname, fvalue in value.items():
            attrs = {
                'name': field_prefix + fname,
                'type': 'checkbox'
            }
            if fvalue:
                attrs['checked'] = 'checked'
            checkboxes.append(format_html(html_template, fname, flatatt(attrs)))
        return mark_safe('<br>'.join(checkboxes))


class AdminCustomerForm(AdminUserChangeForm):
    class Meta:
        widgets = {
            'contact_preferences': JsonCheckboxesWidget()
        }
