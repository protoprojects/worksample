from django import forms

from loans.models import LoanProfileV1


class LoanProfileV1AdminForm(forms.ModelForm):
    class Meta:
        model = LoanProfileV1
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(LoanProfileV1AdminForm, self).__init__(*args, **kwargs)

        if ('advisor' in self.fields) and not self.instance.encompass_never_synced_or_failed():
            # Remove advisor field from editable if loan has been already synced.
            self.fields.pop('advisor')

    def clean_advisor(self):
        if 'advisor' in self.changed_data:
            if self.instance and self.instance.advisor and not self.instance.storage:
                raise forms.ValidationError('No storage exists, please first create storage')
        return self.cleaned_data['advisor']
