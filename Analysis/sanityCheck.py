from collections import defaultdict


class ResultsRatio:
    def __init__(self, fewer_results=0, more_results=0):
        self.fewer_results = fewer_results
        self.more_results = more_results

    def incr_fewer_results(self):
        self.fewer_results += 1

    def incr_more_results(self):
        self.more_results += 1


class SanityCheck(object):
    def __init__(self, nr_dirs=0, nr_pages=0, nr_redirects=0, page_counts: defaultdict = None, requestless_data=0,
                 nr_invalid_urls=0, results_visited_ratio=ResultsRatio()):
        self.nr_dirs = nr_dirs
        self.nr_pages = nr_pages
        self.nr_redirects = nr_redirects
        if page_counts is None:
            self.page_counts = defaultdict(int)
        else:
            self.page_counts = page_counts
        self.requestless_data = requestless_data
        self.nr_invalid_urls = nr_invalid_urls
        self.results_visited_ratio = results_visited_ratio

    def __str__(self):
        return f'Number of data directories: {self.nr_dirs}\n' \
               f'Number of pages: {self.nr_pages}\n' \
               f'Number of pages redirected to outside domain: {self.nr_redirects}\n' \
               f'Number of data-files without requests: {self.requestless_data} \n' \
               f'Number of pages ending up at invalid URL: {self.nr_invalid_urls} \n' \
               f'Summary of #pages visited:\n' \
               f'\t= {self.page_counts}\n' \
               f'Summary of visited/results ratio: \n' \
               f'\t #results < #visited: {self.results_visited_ratio.fewer_results}\n' \
               f'\t #results > #visited: {self.results_visited_ratio.more_results}\n'

    def incr_nr_dirs(self):
        self.nr_dirs += 1

    def incr_nr_pages(self):
        self.nr_pages += 1

    def incr_nr_redirects(self):
        self.nr_redirects += 1

    def incr_nr_invalid_urls(self):
        self.nr_invalid_urls += 1

    def add_to_page_counts(self, page_count: int):
        if page_count < 0:
            raise ValueError('page count cannot be negative')
        else:
            self.page_counts[page_count] += 1

    def incr_requestless(self):
        self.requestless_data += 1

    def add_to_results_ratio(self, nr_results: int, nr_visited: int):
        if nr_results < nr_visited:
            self.results_visited_ratio.incr_fewer_results()
        if nr_results > nr_visited:
            self.results_visited_ratio.incr_more_results()
