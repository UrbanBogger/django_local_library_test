from django.shortcuts import render
from django.views import generic
from .models import Book, Author, BookInstance, Genre
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from .forms import RenewBookForm
from .models import Author
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
import datetime


# Create your views here.
def index(request):
    '''
    View function for home page of site
    :param request:
    :return:
    '''
    word_of_the_day = 'revolution'
    # generate counts of some of the main objects
    num_books = Book.objects.all().count()
    num_instances = BookInstance.objects.all().count()
    # available books (status = 'a')
    num_instances_available = BookInstance.objects.filter(
        status__exact='a').count()
    num_authors = Author.objects.count()  # the 'all()' is implied by default
    num_genres = Genre.objects.count()
    titles_with_word_of_day = list(Book.objects.filter(
        title__icontains=word_of_the_day).values_list('title', flat=True))

    #Number of visits to this view, as counted in the session variable
    num_visits = request.session.get('num_visits', 0)
    request.session['num_visits'] = num_visits + 1

    # render the HTML template index.html with the data in the context variable
    return render(request, 'index.html', context={
        'num_books': num_books, 'num_instances': num_instances,
        'num_instances_available': num_instances_available,
        'num_authors': num_authors, 'num_genres': num_genres,
        'word_of_the_day': word_of_the_day,
        'titles_with_word_of_day': titles_with_word_of_day, 'num_visits':
            num_visits},)


class BookListView(generic.ListView):
    model = Book
    paginate_by = 5


class BookDetailView(generic.DetailView):
    model = Book


class AuthorListView(generic.ListView):
    model = Author
    paginate_by = 10

    def get_queryset(self):
        return Author.objects.get_queryset().order_by('last_name')


class AuthorDetailView(generic.DetailView):
    model = Author


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    '''
    Generic class-based view, listing books on loan to current user
    '''
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(
            borrower=self.request.user).filter(status__exact='o').order_by(
            'due_back')


class AllLoanedBooksListView(PermissionRequiredMixin, generic.ListView):
    '''
    Generic class-based view, listing all loaned books
    '''
    permission_required = 'catalog.can_mark_returned'
    model = BookInstance
    template_name = 'catalog/bookinstance_all_borrowed.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(status__exact='o').exclude(
            borrower=None).order_by('due_back')


@permission_required('catalog.can_mark_returned')
def renew_book_librarian(request, pk):
    '''
    View function for renewing a specific BookInstance by a librarian
    :param request:
    :param pk:
    :return:
    '''
    book_inst = get_object_or_404(BookInstance, pk=pk)

    # if this is a POST request, then process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request
        #  (binding)
        form = RenewBookForm(request.POST)
        # check if the form is valid
        if form.is_valid():
            # process the data in form.cleaned_data as required
            book_inst.due_back = form.cleaned_data['renewal_date']
            book_inst.save()
            # redirect to a new URL
            return HttpResponseRedirect(reverse('all-borrowed'))

    # if this is a GET (or any other method), create the default form
    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(
            weeks=3)
        form = RenewBookForm(initial={'renewal_date': proposed_renewal_date,})

    return render(request, 'catalog/book_renew_librarian.html', {
        'form': form, 'bookinst': book_inst})


class AuthorModelManipulator(PermissionRequiredMixin):
    model = Author
    permission_required = 'catalog.can_mark_returned'
    success_url = reverse_lazy('authors')


class AuthorCreate(AuthorModelManipulator, CreateView):
    fields = '__all__'
    initial = {'date_of_death': '12/10/2016', }


class AuthorUpdate(AuthorModelManipulator, UpdateView):
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']


class AuthorDelete(AuthorModelManipulator, DeleteView):
    pass


# duplicate code for the Book views - refactoring strongly advised; could be
# achieved by creating a base ModelManipulatorView base class
class BookModelView(PermissionRequiredMixin):
    model = Book
    permission_required = 'catalog.can_mark_returned'


class BookCreate(BookModelView, CreateView):
    fields = '__all__'


class BookUpdate(BookModelView, UpdateView):
    fields = ['title', 'author', 'summary', 'genre', 'publication_language']


class BookDelete(BookModelView, DeleteView):
    success_url = reverse_lazy('books')
