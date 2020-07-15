import click
import json
import requests
import pprint

pp = pprint.PrettyPrinter(indent=4)


class File:
    def __init__(self, path):
        self.path = path

    def read(self):
        try:
            with open(self.path, 'r') as file:
                return json.load(file)
        except:
            return []

    def write(self, books):
        with open (self.path, 'w') as file:
            json.dump(books, file)

    def parse_books(self):
        books = []
        file = self.read()
        for item in file:
            books.append(Book(item))
        return books


class Book:
    def __init__(self, info):
        self.title = info.get('title')
        self.author = info.get('author')
        self.ISBN = info.get('ISBN')
        self.start_date = info.get('start_date')
        self.end_date = info.get('end_date')
        self.page_count = info.get('page_count')
        self.chosen_search = None

    def __repr__(self):
        return self.title

    def search_by_title(self):
        return API().results('title', self.title)

    def search_by_author(self):
        return API().results('author', self.author)

    def search_by_author_and_title(self):
        both = []
        byauthor = self.search_by_author()
        bytitle = self.search_by_title()
        for result_bytitle in bytitle:
            for result_byauthor in byauthor:
                if self._found_match(result_bytitle.isbn, result_byauthor.isbn):
                    both.append(result_bytitle)
        choice = self.choose(both)
        return choice

    def _found_match(self, title_isbns, author_isbns):
        if (title_isbns is not None) and (author_isbns is not None):
            for title_isbn in title_isbns:
                if title_isbn in author_isbns:
                    return True

    def choose(self, results):
        if len(results) == 1:
            self.chosen_search = results[0]
        elif len(results) > 1:
            invalid_selection = True
            while invalid_selection:
                for num, result in enumerate(results, start=1):
                    print(f'[{num}] {result}')
                chosen = input('Enter the number of the correct book: ')
                if 0 < int(chosen) < (len(results) + 1):
                    index = int(chosen) - 1
                    self.chosen_search = results[index]
                else:
                    print('Invalid Selection, please try again.')

    def pull_info(self):


class API:
    def __init__(self, isbn=None):
        self.isbn = isbn

    def _search(self, search_type, search_term):
        search_term = search_term.lower().replace(' ', '+')
        url = 'http://openlibrary.org/search.json?' + search_type + '=' + search_term
        r = requests.get(url).json()
        return r

    def results(self, search_type, search_term):
        parsed_results = []
        results = self._search(search_type, search_term)['docs']
        for result in results:
            this_result = SearchResults(result)
            if this_result.title.istitle():
                parsed_results.append(this_result)
        return parsed_results

    def get_info(self):
        pass


class SearchResults:
    def __init__(self, info):
        self.info = info
        self.isbn = info.get('isbn')
        self.title = info.get('title')

    def __repr__(self):
        return f'{self.title} - {self.author} [{self.publish_year}]'

    @property
    def author(self):
        authors = self.info.get('author_name')
        if len(authors) == 0:
            return 'Unknown'
        elif len(authors) > 1:
            return authors.join(' & ')
        else:
            return authors[0]

    @property
    def publish_year(self):
        publish_year = self.info.get('publish_year')
        if len(publish_year) == 0:
            return 'Unknown'
        elif len(publish_year) == 1:
            return publish_year[0]
        else:
            years = sorted(publish_year)
            return years[0]



@click.command()
@click.option('--list_books', is_flag=True, help='Lists the books in the db.')
@click.option('--add', is_flag=True, help='Add a book to the list.')
@click.option('--author', default=None, help='The author of the book you are adding.')
@click.option('--title', default=None, help='The title of the book you are adding.')
@click.option('--end_date', default=None, help='The date you finished the book you are adding.')
@click.option('--search', is_flag=True, help='Pull information from OpenLibrary API')
def main(list_books, add, author, title, end_date, search):
    file = File('./books.json')
    books = file.parse_books()
    if list_books:
        for book in books:
            click.echo(book)
    elif add:
        books.append({'author': author,
                      'title': title,
                      'end_date': end_date
                     })
        file.write(books)
    elif search:
        for book in books:
            print(book.search_by_author_and_title())



if __name__ == '__main__':
    main()
