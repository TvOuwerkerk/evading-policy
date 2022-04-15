from collections import defaultdict
from typing import Dict, List


def sort_dict(dictionary: dict):
    sorted_dict = sorted(list(dictionary.items()), key=lambda i: i[1])
    return dict(sorted_dict)


def get_top_10_from_dict(dictionary: dict):
    return dict(list(sort_dict(dictionary).items())[-10:])


class AnalysisCounter:
    rank_buckets = {'1-12000': lambda x: 0 <= x < 12000,
                    '12001-24000': lambda x: 12000 <= x < 24000,
                    '24001-36000': lambda x: 24000 <= x < 36000,
                    '36001-48000': lambda x: 36000 <= x < 48000,
                    '48001-60000': lambda x: 48000 <= x < 60000}

    def __init__(self, total: defaultdict = None, rank: Dict[str, defaultdict] = None,
                 consent: Dict[str, defaultdict] = None):
        if total is None:
            self.total = defaultdict(int)
        if rank is None:
            self.rank = {key: defaultdict(int) for key in self.rank_buckets.keys()}
        if consent is None:
            self.consent = {'cmp': defaultdict(int), 'no-cmp': defaultdict(int)}

        self.total_entries = 0
        self.cmp_entries = 0
        self.no_cmp_entries = 0
        self.rank_entries = {key: 0 for key in self.rank_buckets.keys()}

    def __str__(self):
        print_total = get_top_10_from_dict(self.total)
        print_consent_list = [(x[0], get_top_10_from_dict(x[1])) for x in self.consent.items()]
        print_rank_list = [(x[0], get_top_10_from_dict(x[1])) for x in self.rank.items()]
        output_string = ''
        
        output_string += 'Total count:\n'
        for x in print_total.items():
            output_string += f'{x[0]}: {x[1]} ({round(x[1]/self.total_entries*100, 1)}%),\n'
        output_string += '\n'

        output_string += 'Consent percentages by bucket:\n'
        for bucket_item in print_consent_list:
            output_string += f'-{bucket_item[0]}-\n'
            denominator = self.cmp_entries if bucket_item[0] == 'cmp' else self.no_cmp_entries
            for x in bucket_item[1].items():
                output_string += f'\t{x[0]}: {x[1]} ({round(x[1]/denominator*100, 1)}%),\n'

        output_string += 'Rank percentages by bucket:\n'
        for bucket_item in print_rank_list:
            output_string += f'-{bucket_item[0]}-\n'
            for x in bucket_item[1].items():
                output_string += f'\t{x[0]}: {x[1]} ({round(x[1]/self.rank_entries[bucket_item[0]]*100, 1)}%),\n'

        return output_string

    def incr_counters(self, rank: int, cmp: str, items: List[str], total_counter=False):
        if not total_counter and not items:
            return

        self.total_entries += 1
        if cmp:
            self.cmp_entries += 1
        else:
            self.no_cmp_entries += 1
        for key in self.rank_buckets.keys():
            if self.rank_buckets[key](rank):
                self.rank_entries[key] += 1

        for item in items:
            self.total[item] += 1
            if cmp:
                self.consent['cmp'][item] += 1
            else:
                self.consent['no-cmp'][item] += 1
            for key in self.rank_buckets.keys():
                if self.rank_buckets[key](rank):
                    self.rank[key][item] += 1
