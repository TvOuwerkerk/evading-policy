import itertools
import json
import urllib.parse
import urllib.parse as parse
import os.path
import re
import tld
from tqdm import tqdm
from pprint import pprint
import fileUtils

DATA_PATH = '.\\Corpus-crawl'
UNSAFE_POLICIES = ['unsafe-url', 'no-referrer-when-downgrade']
SAFE_POLICIES = ['no-referrer', 'origin', 'origin-when-cross-origin',
                 'same-origin', 'strict-origin', 'strict-origin-when-cross-origin']


def get_results_data(data: dict):
    try:
        results_data = data['results']
        return results_data
    except KeyError:
        return None


def report_on_nr_visited(nr_visited, report_domain):
    if nr_visited == 0:
        print(f'No URLs were visited for {report_domain}')
        return
    if nr_visited < 5:
        print(f'Less than 5 URLs visited for {report_domain}: {nr_visited}')
    if nr_visited > 30:
        print(f'More than 30 URLs were visited for {report_domain}: {nr_visited}')


def report_on_unsafe_policy(result, report_domain):
    ref_pol = result['referrer-policy']
    if ref_pol in UNSAFE_POLICIES:
        # TODO For large sets, it is better to forego printing
        # print(f'{report_domain} uses unsafe referrer-policy {ref_pol}')
        return True
    return False


def update_summary_count(leakage, unsafe: bool, circumvent: bool):
    if leakage:
        summary_counters['leakage'] += 1
    if unsafe:
        summary_counters['unsafe-policy'] += 1
    if circumvent:
        summary_counters['circumvention'] += 1


def sort_dict(dictionary: dict):
    sorted_dict = sorted(list(dictionary.items()), key=lambda i: i[1])
    return dict(sorted_dict)


def update_policies_used(new_policies: set, policies_dict: dict):
    for policy in new_policies:
        if policy == '':
            continue
        try:
            policies_dict[policy] += 1
        except KeyError:
            policies_dict[policy] = 1
    return policies_dict


def update_leakage_domains(leakage_domains: set, leakage_dict: dict):
    for domain in leakage_domains:
        try:
            leakage_dict[domain] += 1
        except KeyError:
            leakage_dict[domain] = 1
    return leakage_dict


# TODO: split code into functions for better readability of main code
# TODO: consider leakage from non-front page URLs as more interesting printable result
# TODO: split reporting unsafe global policies from reporting on unsafe request-specific policies

# TODO: leakage to paypal in admin.1upkeyboards, first request, is not reported on
summary_counters = {'leakage': 0, 'sets-policy': 0, 'unsafe-policy': 0, 'circumvention': 0,
                    'policies-used': {}, 'leaked-to': {}}

data_directories = fileUtils.get_data_dirs(DATA_PATH)
no_results = 0
no_results_list = []
for directory in tqdm(data_directories):
    directory_path = os.path.join(DATA_PATH, directory)
    admin_file_path = fileUtils.get_admin_file(directory_path)
    unsafe_policy_on_domain = False
    # TODO: count cases where policy was set through http
    domain_circumvents_policy = False
    encountered_policies = set()
    encountered_leakage = set()

    with open(admin_file_path, 'r') as admin:
        admin_data = json.load(admin)
        # Get results of all pages on this domain, continue if this fails
        results = get_results_data(admin_data)
        if not results:
            # TODO: figure out causes for no results -> redirects on initial landing cause 0 usable results
            # print(f'Error: No results in: {admin_file_path}')
            no_results += 1
            no_results_list.append(os.path.split(admin_file_path)[1])
            continue
        # TODO: handle logging/reporting of outliers
        # report_on_nr_visited(len(results), os.path.split(admin_file_path)[1])

        # Consider results of all crawled pages on this domain
        for r in results:
            # Skip cases where the crawled url has no interesting parts to detect as leakage
            parsed_url = parse.urlparse(r['crawled-url'])
            if parsed_url.path in ['', '/'] and parsed_url.query == '' and parsed_url.fragment == '':
                continue
            crawled_domain = parsed_url.netloc
            try:
                referrer_policy = r['referrer-policy']
                for x in re.split(r'[,|\n| ]', referrer_policy):
                    encountered_policies.add(x)
            except KeyError:
                # TODO: handle logging/reporting of outliers
                # print(f'No referrer-policy found for page: {r["crawled-url"]}')
                continue

            # If the crawled page uses a referrer-policy that has not been seen on this domain, check if it's unsafe
            unsafe_policy_on_domain = report_on_unsafe_policy(r, crawled_domain)

            # If the crawled page uses a safe referrer-policy, there's a chance this is being circumvented
            if referrer_policy in SAFE_POLICIES and 'request-leakage' in r:
                current_leakage = set()
                # Consider all cases of leakage occurring on this page
                for request in r['request-leakage']:
                    request_domain = tld.get_fld(request['request-url'])
                    # If leakage on this page occurs to a domain we've already encountered on a different page, continue
                    if request_domain in encountered_leakage:
                        continue
                    # If we've found a new leak destination, add it to overall encountered and encountered for this page
                    encountered_leakage.add(request_domain)
                    current_leakage.add(request_domain)
                # If we encountered any leakage on this specific page, print accordingly
                if current_leakage:
                    domain_circumvents_policy = True
                    # TODO: handle logging/reporting of specific results
                    # print(f'{crawled_domain} circumvents policy \"{referrer_policy}\" and leaks to:')
                    for leak in current_leakage:
                        if not leak.startswith('www'):
                            leak = f'www.{leak}'
                        # TODO: handle logging/reporting of specific results
                        # print(f'\t{leak}')

        update_summary_count(encountered_leakage, unsafe_policy_on_domain, domain_circumvents_policy)
        summary_counters['policies-used'] = update_policies_used(encountered_policies,
                                                                 summary_counters['policies-used'])
        summary_counters['leaked-to'] = update_leakage_domains(encountered_leakage, summary_counters['leaked-to'])

print('=== SUMMARY ===')
print(f'Admin files without results: {no_results}')
print(no_results_list)
print('')
print(f'Domains counted: {len(data_directories)}')
print(f'Encountered leakages: {summary_counters["leakage"]}')
print(f'Pages with unsafe policy: {summary_counters["unsafe-policy"]}')

print(f'Pages circumventing strict policy: {summary_counters["circumvention"]}')
print(f'Policies used: ({len(summary_counters["policies-used"])})')
pprint(sort_dict(summary_counters['policies-used']), sort_dicts=False)
print('')

leak_dict_length = len(summary_counters['leaked-to'])
print(f'Domains leaked to on circumvention: ({leak_dict_length})')
sliced_dictionary = dict(itertools.islice(sort_dict(summary_counters['leaked-to']).items(),
                                          leak_dict_length - 20, leak_dict_length))
pprint(sliced_dictionary, sort_dicts=False)
