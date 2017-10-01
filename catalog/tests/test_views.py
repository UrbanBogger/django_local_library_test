from django.test import TestCase
from catalog.models import Author
from django.core.urlresolvers import reverse
from django.utils import timezone
import datetime
from catalog.models import BookInstance, Book, Genre, Language
from catalog.views import AuthorCreate
# required to assign a user object as a borrower
from django.contrib.auth.models import User
# required to grant the permission needed to set a book as returned
from django.contrib.auth.models import Permission

class AuthorListViewTest(TestCase):
    num_of_authors_per_page = 10
    num_of_authors = 13

    @classmethod
    def setUpTestData(cls, number_of_authors=num_of_authors):
        # create 13 authors for the pagination test
        number_of_authors = 13
        for author_num in range(number_of_authors):
            Author.objects.create(first_name='Christian %s' % author_num,
                                  last_name = 'Surname %s' % author_num,)

    def test_view_url_exists_at_desired_location(self):
        resp = self.client.get('/catalog/authors/')
        self.assertEqual(resp.status_code, 200)

    def test_view_url_accessible_by_name(self):
        resp = self.client.get(reverse('authors'))
        self.assertEqual(resp.status_code, 200)

    def test_view_uses_correct_template(self):
        resp = self.client.get(reverse('authors'))
        self.assertTemplateUsed(resp, 'catalog/author_list.html')

    def test_pagination_is_ten(self):
        resp = self.client.get(reverse('authors'))
        self.assertTrue('is_paginated' in resp.context)
        self.assertTrue(resp.context['is_paginated'] == True)
        self.assertTrue(len(resp.context['author_list']) ==
                        self.num_of_authors_per_page)

    def test_lists_all_authors(self):
        # get the second page and confirm that it contains the remaining 4
        # authors
        num_of_authors_left = self.num_of_authors - self.num_of_authors_per_page
        resp = self.client.get(reverse('authors') + '?page=2')
        self.assertTrue(len(resp.context['author_list']) ==
                        num_of_authors_left)


class LoanedBookInstancesByUserListViewTest(TestCase):

    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1',
                                              password='12345')
        test_user1.save()
        test_user2 = User.objects.create_user(username='testuser2',
                                              password='12345')
        test_user2.save()

        # create a book
        test_author = Author.objects.create(first_name='John',
                                            last_name='Smith')
        test_genre = Genre.objects.create(name='Fantasy')
        test_language = Language.objects.create(language='English')
        test_book = Book.objects.create(title='Book Title',
                                        summary='My book summary',
                                        isbn='ABCDEFG', author=test_author,
                                        publication_language=test_language)
        # create genre as a post-step
        genre_objects_for_book = Genre.objects.all()
        test_book.genre = genre_objects_for_book
        test_book.save()

        # create 30 BookInstance objects
        num_of_copies = 30
        for copy_of_book in range(num_of_copies):
            return_date = timezone.now() + datetime.timedelta(
                days=copy_of_book % 5)
            if copy_of_book % 2:
                the_borrower = test_user1
            else:
                the_borrower = test_user2
            status = 'm'
            BookInstance.objects.create(
                book=test_book, imprint='Unlikely Imprint, 2016',
                due_back=return_date, borrower=the_borrower, status=status)

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(reverse('my-borrowed'))
        self.assertRedirects(resp, '/accounts/login/?next=/catalog/mybooks/')

    def test_logged_in_uses_correct_template(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))
        # check that our user is logged in
        self.assertEqual(str(resp.context['user']), 'testuser1')
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp,
                                'catalog/bookinstance_list_borrowed_user.html')

    def test_only_borrowed_books_in_list(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))
        # check that initially we don't have any books in the list (no books
        #  on loan)
        self.assertTrue('bookinstance_list' in resp.context)
        self.assertEqual(len(resp.context['bookinstance_list']), 0)
        # change all books to be on loan
        get_ten_books = BookInstance.objects.all()[:10]
        for copy in get_ten_books:
            copy.status = 'o'
            copy.save()

        #verify that there are now borrowed books in the list
        resp = self.client.get(reverse('my-borrowed'))
        self.assertTrue('bookinstance_list' in resp.context)
        # confirm that all books belong to testuser1 and are on loan
        for bookitem in resp.context['bookinstance_list']:
            self.assertEqual(resp.context['user'], bookitem.borrower)
            self.assertEqual('o', bookitem.status)

    def test_pages_ordered_by_due_date(self):
        # Change all books to be on loan
        for copy in BookInstance.objects.all():
            copy.status = 'o'
            copy.save()

        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse('my-borrowed'))

        # Check our user is logged in
        self.assertEqual(str(resp.context['user']), 'testuser1')
        # Check that we got a response "success"
        self.assertEqual(resp.status_code, 200)
        # Confirm that of the items, only 10 are displayed due to pagination.
        self.assertEqual(len(resp.context['bookinstance_list']), 10)

        last_date = 0
        for copy in resp.context['bookinstance_list']:
            if last_date == 0:
                last_date = copy.due_back
            else:
                self.assertTrue(last_date <= copy.due_back)


class RenewBookInstancesViewTest(TestCase):

    def setUp(self):
        test_user1 = User.objects.create_user(username='test',
                                              password='12345')
        test_user1.save()
        test_user2 = User.objects.create_user(username='testuser2',
                                              password='12345')
        test_user2.save()
        permission = Permission.objects.get(name='Set book as returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()

        test_author = Author.objects.create(first_name='John',
                                            last_name='Smith')
        test_genre = Genre.objects.create(name='Fantasy')
        test_language = Language.objects.create(language='English')
        test_book = Book.objects.create(title='Book Title',
                                        summary='My book summary',
                                        isbn='ABCDEFG', author=test_author,
                                        publication_language=test_language)
        # create genre as a post-step
        genre_objects_for_book = Genre.objects.all()
        test_book.genre = genre_objects_for_book
        test_book.save()

        # create a BookInstance object for test_user1
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance1 = BookInstance.objects.create(
            book=test_book, imprint='Unlikely Imprint, 2016',
            due_back=return_date, borrower=test_user1, status='o')

        # create a BookInstance object for test_user2
        return_date = datetime.date.today() + datetime.timedelta(days=5)
        self.test_bookinstance2 = BookInstance.objects.create(
            book=test_book, imprint='Unlikely Imprint, 2016',
            due_back=return_date, borrower=test_user2, status='o')

    def test_redirect_if_not_logged_in(self):
        resp = self.client.get(
            reverse('renew-book-librarian',
                    kwargs={'pk': self.test_bookinstance1.pk,}))
        # manually check redirect (can't use assertRedirect because the
        # redirect URL is unpredictable)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_redirect_if_logged_in_but_not_correct_permission(self):
        login = self.client.login(username='testuser1', password='12345')
        resp = self.client.get(reverse(
            'renew-book-librarian', kwargs={'pk':self.test_bookinstance1.pk,}))
        # manually check redirect
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith('/accounts/login/'))

    def test_logged_in_with_permission_borrowed_book(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse(
            'renew-book-librarian', kwargs={
                'pk': self.test_bookinstance2.pk,}))
        # verify that the system lets us log in - this is our book and we
        # have the right permissions
        self.assertEqual(resp.status_code, 200)

    def test_logged_in_with_permission_another_users_borrowed_book(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse(
            'renew-book-librarian', kwargs={
                'pk': self.test_bookinstance1.pk,}))
        # check that the system allows us to log in - we're a librarian,
        # so we can view any user's book
        self.assertEqual(resp.status_code, 200)

    def test_HTTP404_for_invalid_book_if_logged_in(self):
        import uuid
        # unlikely to match our book instance
        test_uid = uuid.uuid4()
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian',
                                       kwargs={'pk': test_uid,}))
        self.assertEqual(resp.status_code, 404)

    def test_uses_correct_template(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse(
            'renew-book-librarian', kwargs={
                'pk': self.test_bookinstance1.pk,}))
        self.assertEqual(resp.status_code, 200)
        # check that the correct template was used
        self.assertTemplateUsed(resp, 'catalog/book_renew_librarian.html')

    def test_form_renewal_date_initially_has_date_three_weeks_in_future(self):
        login = self.client.login(username='testuser2', password='12345')
        resp = self.client.get(reverse('renew-book-librarian',
                                       kwargs={
                                           'pk': self.test_bookinstance1.pk,}))
        self.assertEqual(resp.status_code, 200)

        date_three_weeks_in_future = datetime.date.today() + \
                                     datetime.timedelta(weeks=3)
        self.assertEqual(resp.context['form'].initial['renewal_date'],
                         date_three_weeks_in_future)

    def test_redirects_to_all_borrowed_book_list_on_success(self):
        login = self.client.login(username='testuser2', password='12345')
        valid_date_in_future = datetime.date.today() + \
            datetime.timedelta(weeks=2)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={
            'pk': self.test_bookinstance1.pk,}),
                                {'renewal_date': valid_date_in_future})
        self.assertRedirects(resp, reverse('all-borrowed'))

    def test_form_invalid_renewal_date_past(self):
        login = self.client.login(username='testuser2', password='12345')
        date_in_past = datetime.date.today() - datetime.timedelta(weeks=1)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={
            'pk': self.test_bookinstance1.pk,}),
                                {'renewal_date': date_in_past})
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(
            resp, 'form', 'renewal_date',
            'Invalid date - specified renewal date is in the past')

    def test_form_invalid_renewal_date_future(self):
        login = self.client.login(username='testuser2', password='12345')
        invalid_date_in_future = datetime.date.today() + datetime.timedelta(
            weeks=5)
        resp = self.client.post(reverse('renew-book-librarian', kwargs={
            'pk': self.test_bookinstance1.pk,}),
                                {'renewal_date': invalid_date_in_future})
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(
            resp, 'form', 'renewal_date', 'Invalid date - renewal date more '
                                          'than 4 weeks in the future')


class AuthorCreateViewTest(TestCase):
    redirection_url = '/accounts/login/?next=/catalog/author/create/'

    def setUp(self):
        test_user1 = User.objects.create_user(username='testuser1',
                                              password='12345')
        test_user1.save()
        test_user2 = User.objects.create_user(username='testuser2',
                                              password='12345')
        test_user2.save()
        permission = Permission.objects.get(name='Set book as returned')
        test_user2.user_permissions.add(permission)
        test_user2.save()

    def make_a_get_request(self, view_name='author_create'):
        response = self.client.get(reverse(view_name))
        return response

    def user_with_correct_permissions_logged_in(self):
        self.client.login(username='testuser2', password='12345')

    def user_without_permissions_logged_in(self):
        self.client.login(username='testuser1', password='12345')

    def test_redirected_if_not_logged_in(self):
        response = self.make_a_get_request()
        self.assertRedirects(response, self.redirection_url)

    def test_user_with_correct_permission_can_access_author_create_page(self):
        self.user_with_correct_permissions_logged_in()
        response = self.make_a_get_request()
        self.assertEqual(response.status_code, 200)

    def test_user_redirected_after_author_added(self):
        redirect_page = '/catalog/authors/'
        new_author = Author.objects.create(first_name='Fyodor',
                                           last_name='Dostoyevsky')
        self.user_with_correct_permissions_logged_in()
        response = self.client.post(reverse('author_create'), {'first_name':
                                    new_author.first_name, 'last_name':
                                    new_author.last_name})
        self.assertRedirects(response, redirect_page)

    def test_new_authors_first_name_required(self):
        self.user_with_correct_permissions_logged_in()
        error_msg = 'This field is required.'
        input_combinations = {'first_name_only': ('John', None),
                              'last_name_only': (None, 'Steinbeck')}
        for input_combination, form_inputs in input_combinations.items():
            response = self.client.post(reverse('author_create'), kwargs={
                        'first_name': form_inputs[0], 'last_name':
                        form_inputs[1]})
            if input_combination.startswith('first'):
                self.assertFormError(response, 'form', 'first_name', error_msg)
            else:
                self.assertFormError(response, 'form', 'last_name', error_msg)

    def test_user_without_permission_redirected(self):
        # given:
        self.user_without_permissions_logged_in()
        # when:
        response = self.make_a_get_request()
        # then:
        self.assertRedirects(response, self.redirection_url)

    def test_that_expected_death_date_rendered(self):
        self.user_with_correct_permissions_logged_in()
        response = self.make_a_get_request()
        self.assertEqual(response.context['form'].initial['date_of_death'],
                         AuthorCreate.initial['date_of_death'])

    def test_correct_template_used(self):
        # given
        correct_template = 'catalog/author_form.html'
        self.user_with_correct_permissions_logged_in()
        # when:
        response = self.make_a_get_request()
        # then:
        self.assertTemplateUsed(response, correct_template)
