import csv
from collections import defaultdict
from typing import List
import fileUtils
from ast import literal_eval
from pprint import pprint

# CONSTANTS
DATA_PATH = fileUtils.get_data_path()
UNSAFE_POLICIES = ['unsafe-url', 'no-referrer-when-downgrade']
SAFE_POLICIES = ['no-referrer', 'origin', 'origin-when-cross-origin',
                 'same-origin', 'strict-origin', 'strict-origin-when-cross-origin']

# INIT
RESULTS_CSV = fileUtils.get_csv_results_file()
POLICIES_COUNTER = {'total': defaultdict(int),
                    'rank': {'bucket1': defaultdict(int), 'bucket2': defaultdict(int)},
                    'consent': {'cmp': defaultdict(int), 'no-cmp': defaultdict(int)}}

LEAKAGE_COUNTER = {'total': defaultdict(int),
                   'rank': {'bucket1': defaultdict(int), 'bucket2': defaultdict(int)},
                   'consent': {'cmp': defaultdict(int), 'no-cmp': defaultdict(int)}}


def sort_dict(dictionary: dict):
    sorted_dict = sorted(list(dictionary.items()), key=lambda i: i[1])
    return dict(sorted_dict)


# TODO: reporting global policies vs request-specific policies (add to results data in postProcessing)
with open(RESULTS_CSV, 'r', newline='') as results_csv:
    csv_reader = csv.reader(results_csv)
    for row in csv_reader:
        domain = row[0]
        rank = int(row[1])
        cmp = row[2]
        policies: List[str] = literal_eval(row[3])
        leakage_domains: List[str] = literal_eval(row[4])
        # TODO: Note, using just this file currently only shows leakages and policies aggregated on a whole domain
        #       It does not allow us to claim anything about circumvention.

        for policy in policies:
            POLICIES_COUNTER['total'][policy] += 1
            if cmp:
                POLICIES_COUNTER['consent']['cmp'][policy] += 1
            else:
                POLICIES_COUNTER['consent']['no-cmp'][policy] += 1

        for domain in leakage_domains:
            LEAKAGE_COUNTER['total'][domain] += 1
            if cmp:
                LEAKAGE_COUNTER['consent']['cmp'][domain] += 1
            else:
                LEAKAGE_COUNTER['consent']['no-cmp'][domain] += 1
print("===Policy===")
print(dict(list(sort_dict(POLICIES_COUNTER['consent']['cmp']).items())[:10]))
print(dict(list(sort_dict(POLICIES_COUNTER['consent']['no-cmp']).items())[:10]))

print("===Leakage===")
print(dict(list(sort_dict(LEAKAGE_COUNTER['consent']['cmp']).items())[-10:]))
print(dict(list(sort_dict(LEAKAGE_COUNTER['consent']['no-cmp']).items())[-10:]))

pprint(sort_dict(POLICIES_COUNTER['total']), sort_dicts=False)
