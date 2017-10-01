#from django.test import TestCase
from django.test import SimpleTestCase
import datetime
from django.utils import timezone
from catalog.forms import RenewBookForm

class RenewBookFormTest(SimpleTestCase):

    def get_form_data(self, date):
        return {'renewal_date': date}

    def get_renew_book_form(self, date=None):
        if date:
            form_data = self.get_form_data(date)
            return RenewBookForm(data=form_data)
        return RenewBookForm()

    def test_renew_form_date_field_label(self):
        form = self.get_renew_book_form()
        self.assertTrue(form.fields['renewal_date'].label is None or
                        form.fields['renewal_date'].label == 'renewal_date')

    def test_renew_form_date_field_help_text(self):
        form = self.get_renew_book_form()
        self.assertEqual(form.fields['renewal_date'].help_text,
                         'Enter a date between now and 4 weeks (default 3).')

    def test_renew_form_date_in_past(self):
        date = datetime.date.today() - datetime.timedelta(days=1)
        form = self.get_renew_book_form(date)
        self.assertFalse(form.is_valid())

    def test_renew_form_date_too_far_in_future(self):
        date = datetime.date.today() + datetime.timedelta(weeks=4) + \
               datetime.timedelta(days=1)
        form = self.get_renew_book_form(date)
        self.assertFalse(form.is_valid())

    def test_renew_form_date_today(self):
        date = datetime.date.today()
        form = self.get_renew_book_form(date)
        self.assertTrue(form.is_valid())

    def test_renew_form_date_max(self):
        date = timezone.now() + datetime.timedelta(weeks=4)
        form = self.get_renew_book_form(date)
        self.assertTrue(form.is_valid())
