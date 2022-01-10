class PageCounts:
    def __init__(self, equals_zero=0, less_than_21=0, equals_21=0, greater_than_21=0):
        self.equals_zero = equals_zero
        self.less_than_21 = less_than_21
        self.equals_21 = equals_21
        self.greater_than_21 = greater_than_21

    def incr_equals_0(self):
        self.equals_zero += 1

    def incr_less_than_21(self):
        self.less_than_21 += 1

    def incr_equals_21(self):
        self.equals_21 += 1

    def incr_greater_than_21(self):
        self.greater_than_21 += 1


class ResultsRatio:
    def __init__(self, fewer_results=0, more_results=0):
        self.fewer_results = fewer_results
        self.more_results = more_results

    def incr_fewer_results(self):
        self.fewer_results += 1

    def incr_more_results(self):
        self.more_results += 1


class SanityCheck(object):
    def __init__(self, nr_dirs=0, nr_redirects=0, page_counts=PageCounts(), requestless_data=0,
                 results_visited_ratio=ResultsRatio()):
        self.nr_dirs = nr_dirs
        self.nr_redirects = nr_redirects
        self.page_counts = page_counts
        self.requestless_data = requestless_data
        self.results_visited_ratio = results_visited_ratio

    def __str__(self):
        return f'Number of data directories: {self.nr_dirs}\n' \
               f'Number of pages redirected to outside domain: {self.nr_redirects}\n'\
               f'Summary of #pages visited:\n' \
               f'\t=0 : {self.page_counts.equals_zero}\n' \
               f'\t<21: {self.page_counts.less_than_21}\n' \
               f'\t=21: {self.page_counts.equals_21}\n' \
               f'\t>21: {self.page_counts.greater_than_21}\n' \
               f'Number of data-files without requests: {self.requestless_data} \n' \
               f'Summary of visited/results ratio: \n' \
               f'\t #results < #visited: {self.results_visited_ratio.fewer_results}\n' \
               f'\t #results > #visited: {self.results_visited_ratio.more_results}\n'

    def incr_nr_dirs(self):
        self.nr_dirs += 1

    def incr_nr_redirects(self):
        self.nr_redirects += 1

    def add_to_page_counts(self, page_count: int):
        if page_count < 0:
            raise ValueError
        if page_count == 0:
            self.page_counts.incr_equals_0()
        elif page_count < 21:
            self.page_counts.incr_less_than_21()
        elif page_count == 21:
            self.page_counts.incr_equals_21()
        elif page_count > 21:
            self.page_counts.incr_greater_than_21()

    def incr_requestless(self):
        self.requestless_data += 1

    def add_to_results_ratio(self, nr_results: int, nr_visited: int):
        if nr_results < nr_visited:
            self.results_visited_ratio.incr_fewer_results()
        if nr_results > nr_visited:
            self.results_visited_ratio.incr_more_results()
