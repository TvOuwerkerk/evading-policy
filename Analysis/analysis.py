import csv
import sys
from typing import List, Dict

from tld import get_fld

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
TOTAL_COUNTER = AnalysisCounter()

POLICY_COUNTER = AnalysisCounter()
CMP_COUNTER = AnalysisCounter()

PAGE_LEAKAGE_COUNTER = AnalysisCounter()
DOMAIN_LEAKAGE_COUNTER = AnalysisCounter()
ORGANISATION_COUNTER = AnalysisCounter()
FACEBOOK_LEAKAGE_COUNTER = AnalysisCounter()
RANK_LIST = []


def sort_dict(dictionary: dict):
    sorted_dict = sorted(list(dictionary.items()), key=lambda i: i[1])
    return dict(sorted_dict)


def get_rank_list():
    return RANK_LIST


def get_domain_map():
    domain_map_full = fileUtils.get_domain_map_file()
    return {k: v['entityName'] for (k, v) in domain_map_full.items()}


def get_counters():
    return {'domain': DOMAIN_LEAKAGE_COUNTER,
            'page': PAGE_LEAKAGE_COUNTER,
            'total': TOTAL_COUNTER,
            'organisation': ORGANISATION_COUNTER,
            'cmp': CMP_COUNTER}


# TODO: reporting global policies vs request-specific policies (add to results data in postProcessing)
with open(RESULTS_CSV, 'r', newline='') as results_csv:
    csv_reader = csv.reader(results_csv)
    domain_mapping: Dict[str, str] = get_domain_map()
    mapped_domains = {}
    for row in csv_reader:
        domain = row[0]
        rank = int(row[1])
        cmp = row[2]
        policies: List[str] = literal_eval(row[3])
        leakage_pages: List[str] = literal_eval(row[4])
        leakage_pages = list(map(lambda u: u[4:] if u.startswith('www') else u, leakage_pages))
        leakage_domains: List[str] = list(set(map(lambda u: get_fld(f'https://{u}'), leakage_pages)))
        leakage_amounts: List[str] = []
        amount = 1
        for leakage in literal_eval(row[4]):
            leakage_amounts.append(f'≥ {amount}')
            amount += 1

        leakage_organisations = set()
        for leakage in leakage_domains:
            try:
                leakage_organisations.add(domain_mapping[get_fld(f'https://{leakage}')])
            except KeyError:
                continue

        RANK_LIST.append(rank)
        TOTAL_COUNTER.incr_counters(rank, cmp, leakage_amounts)
        POLICY_COUNTER.incr_counters(rank, cmp, policies)
        if cmp:
            CMP_COUNTER.incr_counters(rank, cmp, [cmp])

        PAGE_LEAKAGE_COUNTER.incr_counters(rank, cmp, leakage_pages)
        DOMAIN_LEAKAGE_COUNTER.incr_counters(rank, cmp, leakage_domains)
        ORGANISATION_COUNTER.incr_counters(rank, cmp, list(leakage_organisations))
        FACEBOOK_LEAKAGE_COUNTER.incr_counters(rank, cmp, [u for u in leakage_pages if get_fld(f'https://{u}') == 'facebook.com'])

#print("===Policy===")
#print(POLICY_COUNTER)

#print("===Leakage to Pages===")
#print(PAGE_LEAKAGE_COUNTER)

#print("===Leakage to Domains===")
#print(DOMAIN_LEAKAGE_COUNTER)

#print(FACEBOOK_LEAKAGE_COUNTER)

#print(ORGANISATION_COUNTER)
