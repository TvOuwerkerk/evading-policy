import csv
import sys
from typing import List, Dict

from tld import get_fld

import fileUtils
from analysisCounter import AnalysisCounter
from ast import literal_eval

# CONSTANTS
DATA_PATH = fileUtils.get_data_path()

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
        maxInt = int(maxInt / 10)

RESULTS_CSV = fileUtils.get_csv_results_file()
TOTAL_COUNTER = AnalysisCounter()

POLICY_COUNTER = AnalysisCounter()
CMP_COUNTER = AnalysisCounter()

PAGE_LEAKAGE_COUNTER = AnalysisCounter()
DOMAIN_LEAKAGE_COUNTER = AnalysisCounter()
USAGE_COUNTER = AnalysisCounter()
ORGANISATION_COUNTER = AnalysisCounter()

ENDPOINTS = ['google-analytics.com', 'facebook.com', 'doubleclick.net', 'google.com', 'google.nl', 'pinterest.com',
             'nr-data.net', 'twitter.com', 'googlesyndication.com', 'googleadservices.com', 'trustpilot.com', 't.co',
             'linkedin.com', 'gstatic.com', 'paypal.com', 'cookiebot.com', 'yotpo.com', 'bazaarvoice.com',
             'cquotient.com', 'go-mpulse.net', 'googlevideo.com', 'bing.com', 'amazon-adsystem.com', 'ebay.com']
ENDPOINT_LEAKAGE_COUNTERS = {}
for e in ENDPOINTS:
    ENDPOINT_LEAKAGE_COUNTERS[e] = AnalysisCounter()

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
            'usage': USAGE_COUNTER,
            'page': PAGE_LEAKAGE_COUNTER,
            'total': TOTAL_COUNTER,
            'organisation': ORGANISATION_COUNTER,
            'cmp': CMP_COUNTER,
            'policy': POLICY_COUNTER,
            'endpoints': ENDPOINT_LEAKAGE_COUNTERS}


organisation_domains = set()
with open(RESULTS_CSV, 'r', newline='') as leakage_results_csv:
    csv_reader = csv.reader(leakage_results_csv)
    domain_mapping: Dict[str, str] = get_domain_map()
    mapped_domains = {}
    for row in csv_reader:
        domain = row[0]
        rank = int(row[1])
        cmp = row[2]
        leakage_pages: List[str] = literal_eval(row[3])
        leakage_pages = list(map(lambda u: u[4:] if u.startswith('www') else u, leakage_pages))
        leakage_domains: List[str] = list(set(map(lambda u: get_fld(u, fix_protocol=True), leakage_pages)))
        leakage_amounts: List[str] = []
        amount = 1
        for leakage in literal_eval(row[3]):
            leakage_amounts.append(f'≥ {amount}')
            amount += 1
        third_party_pages_used = literal_eval(row[4])


        def page_used_filter(page: str):
            return '' if 'yass/' in page else get_fld(page, fix_protocol=True)


        third_party_domains_used: List[str] = list(map(page_used_filter, third_party_pages_used))

        leakage_organisations = set()
        for leakage in leakage_domains:
            try:
                leakage_organisations.add(domain_mapping[get_fld(f'https://{leakage}')])
                organisation_domains.add(get_fld(leakage, fix_protocol=True))
            except KeyError:
                continue

        RANK_LIST.append(rank)
        TOTAL_COUNTER.incr_counters(rank, cmp, leakage_amounts, total_counter=True)
        USAGE_COUNTER.incr_counters(rank, cmp, list(set(third_party_domains_used)), total_counter=True)
        if cmp:
            if cmp == 'onetrust1':
                cmp = 'onetrust-OLD'
            elif cmp == 'onetrust2':
                cmp = 'onetrust-LI'
            CMP_COUNTER.incr_counters(rank, cmp, [cmp])

        PAGE_LEAKAGE_COUNTER.incr_counters(rank, cmp, leakage_pages)
        DOMAIN_LEAKAGE_COUNTER.incr_counters(rank, cmp, leakage_domains)
        ORGANISATION_COUNTER.incr_counters(rank, cmp, list(leakage_organisations))
        for key in ENDPOINT_LEAKAGE_COUNTERS:
            if key == 'gstatic.com':
                trimmed_pages_gstatic = list(set(['/'.join(p.split('/')[:4]) if p.startswith('fonts.gstatic.com/s/')
                                                  else p for p in leakage_pages]))
                ENDPOINT_LEAKAGE_COUNTERS[key].incr_counters(
                    rank, cmp, [u for u in trimmed_pages_gstatic if get_fld(f'https://{u}') == key])
            elif key == 'google.nl':
                trimmed_pages_googlenl = ['/'.join(p.split('/')[:3]) if 'google.nl/pagead/1p-user-list' in p
                                          or 'google.nl/pagead/1p-conversion' in p
                                          else p for p in leakage_pages]
                ENDPOINT_LEAKAGE_COUNTERS[key].incr_counters(
                    rank, cmp, [u for u in trimmed_pages_googlenl if get_fld(f'https://{u}') == key])
            else:
                ENDPOINT_LEAKAGE_COUNTERS[key].incr_counters(
                    rank, cmp, [u for u in leakage_pages if get_fld(f'https://{u}') == key])
