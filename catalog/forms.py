from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
import datetime # to check the renewal date range


class RenewBookForm(forms.Form):
    renewal_date = forms.DateField(
        help_text="Enter a date between now and 4 weeks (default 3).")

    def clean_renewal_date(self):
        data = self.cleaned_data['renewal_date']
        # check that the date is not in the past
        if data < datetime.date.today():
            raise ValidationError(_(
                'Invalid date - specified renewal date is in the past'))
        # check that the date is in the range that the librarian is allowed
        # to change (+4 weeks)
        if data > datetime.date.today() + datetime.timedelta(weeks=4):
            raise ValidationError(_('Invalid date - renewal date more than '
                                    '4 weeks in the future'))
        # remember to always return cleaned data
        return data
