import click
import json
import requests
import pprint

from datetime import datetime
from difflib import SequenceMatcher

pp = pprint.PrettyPrinter(indent=4)


class Booklist:
    def __init__(self, path):
        self.path = path
        self.books = self.parse_books()

    def read(self):
        try:
            with open(self.path, 'r') as file:
                return json.load(file)
        except:
            return []

    def write(self):
        all_books = []
        for book in self.books:
            all_books.append(book.to_json())
        with open (self.path, 'w') as file:
            contents = ', '.join(all_books)
            file.write(f'[{contents}]')

    def parse_books(self):
        books = []
        file = self.read()
        for item in file:
            books.append(Book(item))
        return books

    def add(self, author, title, start_date, end_date):
        book = Book({'author': author,
                     'title': title,
                     'start_date': start_date,
                     'end_date': end_date})
        book.search()
        self.books.append(book)
        self.write()

    def edit(self):
        book = select(self.books)
        book.edit()
        self.write()

    def list_books(self):
        for book in self.books:
            click.echo(book)


class Book:
    def __init__(self, info):
        self.title = info.get('title')
        self.author = info.get('author')
        self.ISBN = info.get('ISBN')
        self.page_count = info.get('page_count')
        self.start_date = info.get('start_date')
        self.end_date = info.get('end_date')

    def __repr__(self):
        return f'{self.title} by {self.author} - [{self.start_date}/{self.end_date}]'

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, indent=2)

    def search(self, override=False):
        if self.ISBN is None:
            Search(self).by_author_and_title()

    def edit(self):
        options = [f'Title: {self.title}', f'Author: {self.author}', f'Start Date: {self.start_date}', f'End Date: {self.end_date}']
        field_to_edit = select(options)
        new_value = input('Enter the new information: ')
        if 'Title' in field_to_edit:
            self.title = new_value
        if 'Author' in field_to_edit:
            self.author = new_value
        if 'Start Date' in field_to_edit:
            self.start_date = new_value
        if 'End Date' in field_to_edit:
            self.end_date = new_value

class Search:
    def __init__(self, book):
        self.book = book
        self.bytitle = []
        self.byauthor = []
        self.chosen_search = None

    def _get_via_api(self, search_type, search_term):
        search_term = search_term.lower().replace(' ', '+')
        url = 'http://openlibrary.org/search.json?' + search_type + '=' + search_term
        r = requests.get(url).json()
        return r

    def _search(self, search_type, search_term):
        parsed_results = []
        results = self._get_via_api(search_type, search_term)['docs']
        for result in results:
            parsed_results.append(SearchResults(result))
        return parsed_results

    def _by_title(self):
        self.bytitle = self._search('title', self.book.title)

    def _by_author(self):
        self.byauthor = self._search('author', self.book.author)

    def _get_intersection(self):
        both = []
        for result_bytitle in self.bytitle:
            for result_byauthor in self.byauthor:
                if self._found_match(result_bytitle.isbn, result_byauthor.isbn):
                    if result_bytitle.page_count is not None:
                        both.append(result_bytitle)
        return both

    def _fuzzy_search(self):
        if self.byauthor == [] and self.bytitle != []:
            self._fuzzy_search_for_author()
            return True
        elif self.byauthor != [] and self.bytitle == []:
            self._fuzzy_search_for_title()
            return True
        elif self.byauthor == [] and self.bytitle == []:
            print(f'Neither author nor title found for {self.book.title} by {self.book.author}. Please manually edit this entry.')
            return False
        return True

    def _found_match(self, title_isbns, author_isbns):
        if (title_isbns is not None) and (author_isbns is not None):
            for title_isbn in title_isbns:
                if title_isbn in author_isbns:
                    return True

    def _fuzzy_search_for_title(self):
        highest_match = 0.0
        highest_title = ''
        for result in self.byauthor:
            match_ratio = SequenceMatcher(None, self.book.title, result.title).ratio()
            if match_ratio > highest_match:
                highest_match = match_ratio
                highest_title = result.title
        if self._confirm_edit('title', self.book.title, highest_title):
            self.book.title = highest_title
            self._by_title()

    def _fuzzy_search_for_author(self):
        highest_match = 0.0
        highest_author = ''
        for result in self.bytitle:
            for author in result.author.split(' & '):
                match_ratio = SequenceMatcher(None, self.book.author, author).ratio()
                if match_ratio > highest_match:
                    highest_match = match_ratio
                    highest_author = author
        if self._confirm_edit('author', self.book.author, highest_author):
            self.book.author = highest_author
            self._by_author()

    def _confirm_edit(self, option, old_info, new_info):
        invalid_selection = True
        while invalid_selection:
            selection = input(f'Change the book {option} from "{old_info}" to "{new_info}"? [y/n] ')
            if selection.lower() in ['y', 'yes']:
                return True
            elif selection.lower() in ['n', 'no']:
                return False

    def _choose(self, results):
        self.chosen_search = select(results)

    def by_author_and_title(self):
        self._by_author()
        self._by_title()
        if self._fuzzy_search():
            self._choose(self._get_intersection())
            self.book.ISBN = self.chosen_search.isbn[0]
            self.book.page_count = self.chosen_search.page_count


class SearchResults:
    def __init__(self, info):
        self.info = info
        self.isbn = info.get('isbn')
        self.title = info.get('title').title()

    def __repr__(self):
        return f'{self.title} - {self.author} [{self.publish_year}]'

    @property
    def author(self):
        authors = self.info.get('author_name')
        if authors is not None:
            if len(authors) > 1:
                return ' & '.join(authors)
            else:
                return authors[0]
        return 'Unknown'

    @property
    def publish_year(self):
        publish_year = self.info.get('publish_year')
        if publish_year is not None:
            if len(publish_year) == 1:
                return publish_year[0]
            else:
                years = sorted(publish_year)
                return years[0]
        return 'Unknown'

    @property
    def page_count(self):
        if self.isbn != None:
            for isbn in self.isbn:
                page_count = self.get_pages(isbn)
                if page_count is not None:
                    return page_count
        return None

    def _search(self, isbn):
        url = f'http://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data'
        r = requests.get(url).json()
        return r

    def get_pages(self, isbn):
        try:
            return self._search(isbn)[f'ISBN:{isbn}']['number_of_pages']
        except KeyError:
            return None

@click.command()
@click.option('--list_books', is_flag=True, help='Lists the books in the db.')
@click.option('--add', is_flag=True, help='Add a book to the list.')
@click.option('--author', default=None, help='The author of the book you are adding.')
@click.option('--title', default=None, help='The title of the book you are adding.')
@click.option('--start_date', default=None, help='The date you started the book you are adding.')
@click.option('--end_date', default=None, help='The date you finished the book you are adding.')
@click.option('--edit', is_flag=True, help='Edit a book entry.')
def main(list_books, add, author, title, start_date, end_date, edit):
    booklist = Booklist('./books.json')
    books = booklist.books
    if list_books:
        booklist.list_books()
    elif add:
        booklist.add(author, title, start_date, end_date)
    elif edit:
        booklist.edit()

def select(options):
    while True:
        if len(options) == 1:
            return options[0]
        elif len(options) > 1:
            for num, option in enumerate(options, start=1):
                print(f'[{num}] {option}')
            chosen = input('Enter the number corresponding to your choice: ')
            if 0 < int(chosen) < (len(options) + 1):
                return options[int(chosen) - 1]
            else:
                print('Invalid Selection, please try again.')

if __name__ == '__main__':
    main()
