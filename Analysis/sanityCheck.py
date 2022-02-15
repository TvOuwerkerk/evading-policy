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
    def __init__(self, nr_dirs=0, nr_invalid_dirs=0, nr_files=0, nr_redirects=0, nr_outside_requests=0, page_counts: defaultdict = None, requestless_data=0,
                 nr_invalid_urls=0, results_visited_ratio=ResultsRatio()):
        self.nr_dirs = nr_dirs
        self.nr_invalid_dirs = nr_invalid_dirs
        self.nr_files = nr_files
        self.nr_redirects = nr_redirects
        self.nr_outside_requests = nr_outside_requests
        if page_counts is None:
            self.page_counts = defaultdict(int)
        else:
            self.page_counts = page_counts
        self.requestless_data = requestless_data
        self.nr_invalid_urls = nr_invalid_urls
        self.results_visited_ratio = results_visited_ratio

    def __str__(self):
        return f'Number of data directories: {self.nr_dirs}\n' \
               f'Number of disregarded data directories: {self.nr_invalid_dirs}\n' \
               f'Total number of valid data files: {self.nr_files}\n' \
               f'\t number of which redirected to outside domain: {self.nr_redirects}\n' \
               f'\t number of which were created for outside domain: {self.nr_outside_requests}\n' \
               f'\t number of which without requests: {self.requestless_data} \n' \
               f'\t number of which ending up at an invalid URL: {self.nr_invalid_urls} \n' \
               f'Summary of #data files per domain:\n' \
               f'\t= {self.page_counts}\n' \
               f'Summary of visited/results ratio: \n' \
               f'\t #results < #visited: {self.results_visited_ratio.fewer_results}\n' \
               f'\t #results > #visited: {self.results_visited_ratio.more_results}\n'

    def incr_nr_dirs(self):
        self.nr_dirs += 1

    def incr_nr_invalid_dirs(self):
        self.nr_invalid_dirs += 1

    def incr_nr_files(self):
        self.nr_files += 1

    def incr_nr_redirects(self):
        self.nr_redirects += 1

    def incr_nr_outside_requests(self, amt=1):
        self.nr_outside_requests += amt

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
