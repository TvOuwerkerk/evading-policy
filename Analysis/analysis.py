import csv
import sys
from typing import List

import tld

import fileUtils
from analysisCounter import AnalysisCounter
from ast import literal_eval

# CONSTANTS
DATA_PATH = fileUtils.get_data_path()
UNSAFE_POLICIES = ['unsafe-url', 'no-referrer-when-downgrade']
SAFE_POLICIES = ['no-referrer', 'origin', 'origin-when-cross-origin',
                 'same-origin', 'strict-origin', 'strict-origin-when-cross-origin']

# INIT
maxInt = sys.maxsize
# Loop found on https://stackoverflow.com/questions/15063936/csv-error-field-larger-than-field-limit-131072
while True:
    # decrease the maxInt value by factor 10
    # as long as the OverflowError occurs.
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)

RESULTS_CSV = fileUtils.get_csv_results_file()
policy_counter = AnalysisCounter()
page_leakage_counter = AnalysisCounter()
domain_leakage_counter = AnalysisCounter()
facebook_leakage_counter = AnalysisCounter()


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
        leakage_pages: List[str] = literal_eval(row[4])
        leakage_pages = list(map(lambda u: u[4:] if u.startswith('www') else u, leakage_pages))
        leakage_domains: List[str] = list(set(map(lambda u: tld.get_fld(f'https://{u}'), leakage_pages)))
        # TODO: Note, using just this file currently only shows leakages and policies aggregated on a whole domain
        #       It does not allow us to claim anything about circumvention.

        if 'strict-origin-when-cross-origin' in policies:
            policies.remove('strict-origin-when-cross-origin')
        policy_counter.incr_counters(rank, cmp, policies)
        page_leakage_counter.incr_counters(rank, cmp, leakage_pages)
        domain_leakage_counter.incr_counters(rank, cmp, leakage_domains)
        facebook_leakage_counter.incr_counters(rank, cmp, [u for u in leakage_pages if tld.get_fld(f'https://{u}') == 'facebook.com'])

print("===Policy===")
print(policy_counter)

print("===Leakage to Pages===")
print(page_leakage_counter)

print("===Leakage to Domains===")
print(domain_leakage_counter)

print(facebook_leakage_counter)