import csv
import json
import os.path

import urllib.parse as parse
from tld import get_fld
import validators

from collections import defaultdict
from tqdm import tqdm

from sanityCheck import SanityCheck
import fileUtils
from dataFileHandling import set_file_output_redirected_url, get_request_info, get_leakage_pages

RESULTS_CSV = fileUtils.get_csv_results_file()
POLICY_RESULTS_JSON = fileUtils.get_policy_results_file()
TRANCO_RANKING = fileUtils.get_tranco_ranking()


def find_cmp_occurrences_in_logs():
    """
    Scans the log files for CMPs detected when websites were visited.
    :return: dictionary with keys=websites and values=CMPs found on each website
    """
    log_files = fileUtils.get_log_files()
    cmp_occurrences = {}
    for log_file in log_files:
        with open(log_file, 'r', encoding='utf-8') as log_inp:
            lines = log_inp.readlines()
            for line in lines:
                # Line structure: "[...] CMP detected on https://www.example.com/: {"cmpName":"exampleCMP"}"
                if 'CMP detected on' in line:
                    found_url = line.split('CMP detected on ')[1].split(' ')[0][:-1]
                    found_cmp = line.split('{')[-1].split(':"')[1].split('"}')[0]
                    cmp_occurrences[parse.urlunsplit(parse.urlsplit(found_url))] = found_cmp
    return cmp_occurrences


def verify_data(sanity_counter: SanityCheck, data_object: dict):
    """
    Perform a number of checks on collected data and update the SanityCheck counter object accordingly.
    :return: Boolean containing whether the given data_object was valid and the updated counter object.
    """
    crawled = parse.urlunparse(parse.urlparse(data_object['initialUrl']))
    final = data_object['finalUrl']

    # If the page visited did not end up at a valid url, skip this entry
    if not validators.url(final):
        sanity_counter.incr_nr_invalid_urls()
        return False, sanity_counter

    # If this file contains data on a domain outside the intended domain, ignore the file.
    if get_fld(crawled) != get_fld(final):
        sanity_counter.incr_nr_redirects()
        return False, sanity_counter

    # Check if requests data exists
    try:
        requests = list(data_object['data']['requests'])
        if len(requests) == 0:
            raise KeyError
    except KeyError:
        sanity_counter.incr_requestless()
        return False, sanity_counter

    return True, sanity_counter


def get_domain_rank(domain: str):
    try:
        return TRANCO_RANKING.index(domain)
    except ValueError:
        return -1


# Find all directories which have data saved to them
data_directories = fileUtils.get_data_dirs()
cmp_lookup_dict = find_cmp_occurrences_in_logs()
sanity_check = SanityCheck()
for directory in tqdm(data_directories):
    # Get the crawled website and init variables.
    dir_name = os.path.basename(directory)[5:]
    csv_results_row = [dir_name, get_domain_rank(dir_name), None]

    # Variables to save policy data to
    set_policy = ''
    req_pol_1stparty = set()
    req_pol_3rdparty = defaultdict(set)
    resp_pol_3rdparty = defaultdict(set)

    # Variables to save leakage-related data to
    leakage_to_domains = set()
    third_parties_on_domain = set()

    sanity_check.incr_nr_dirs()

    # Find all .json files that contain crawled data
    results_files = fileUtils.get_data_files(directory)
    sanity_check.incr_nr_outside_requests(amt=(len(results_files['total'])-len(results_files['valid'])))
    files = results_files['valid']
    # If the directory has too few valid files, skip the directory
    if len(files) < 2:
        sanity_check.incr_nr_invalid_dirs()
        continue
    sanity_check.add_to_page_counts(len(files))

    # Add number of visited websites in admin file to sanity check.
    with open(fileUtils.get_admin_file(directory), 'r', encoding='utf-8') as admin_file:
        nr_visited = len(list(json.load(admin_file)['visited']))
        sanity_check.add_to_results_ratio(len(files), nr_visited)

    for file in files:
        sanity_check.incr_nr_files()
        with open(file, 'r', encoding='utf-8') as data_file:
            # Load the data gathered from a page visit
            data: dict = json.load(data_file)

            # Get the visited url (intended and actual)
            crawled_url = parse.urlunparse(parse.urlparse(data['initialUrl']))
            final_url = data['finalUrl']

            # Verify if gathered data is valid
            verified, sanity_check = verify_data(sanity_check, data)
            if not verified:
                continue

            # Create file_output object, containing all results that need to be saved to the admin-file later
            file_output = {'crawled-url': crawled_url,
                           'CMP-encountered': '',
                           'redirected-url': '',
                           'referrer-policy': '',
                           'req_pol_1stparty': set(),
                           'req_pol_3rdparty': {},
                           'resp_pol_3rdparty': {},
                           'request-leakage': [],
                           'third-parties': []}

            # Set 'redirected-url' value
            file_output = set_file_output_redirected_url(file_output, crawled_url, final_url)

            # Add CMP to csv output
            if final_url in cmp_lookup_dict:
                file_output['CMP-encountered'] = cmp_lookup_dict[final_url]
                # If a CMP was not already set for this domain, set it now
                if csv_results_row[2] is None:
                    csv_results_row[2] = cmp_lookup_dict[final_url]

            for request in list(data['data']['requests']):
                if request['type'] == 'WebSocket':
                    continue
                # Add to referrer-policy, policy sets/dictionaries , policies-used, and request-leakage entries
                file_output = get_request_info(request, file_output, crawled_url, final_url)

            if not set_policy:
                set_policy = file_output['referrer-policy']
            elif file_output['referrer-policy'] and set_policy != file_output['referrer-policy']:
                print(f"Different response policies in {dir_name}: {set_policy} and {file_output['referrer-policy']}")

            # Add encountered referrer policies to set and dicts keeping track of them
            req_pol_1stparty.update(file_output['req_pol_1stparty'])
            for key in file_output['req_pol_3rdparty']:
                req_pol_3rdparty[key].update(file_output['req_pol_3rdparty'][key])
            for key in file_output['resp_pol_3rdparty']:
                resp_pol_3rdparty[key].update(file_output['resp_pol_3rdparty'][key])

            leakage_to_domains.update(get_leakage_pages(file_output['request-leakage']))
            third_parties_on_domain.update(file_output['third-parties'])

            # Remove items for which values have not been set
            file_output = {k: v for k, v in file_output.items() if v}
            fileUtils.save_data_to_admin(file_output, directory)

    csv_results_row.append(list(leakage_to_domains))  # Add list of domains being leaked to on this domain to result
    csv_results_row.append(list(third_parties_on_domain))  # Add list of third parties this domain makes requests to
    with open(RESULTS_CSV, 'a', newline='') as leakage_results_csv:
        results_writer = csv.writer(leakage_results_csv)
        results_writer.writerow(csv_results_row)  # When done with this data folder, add its results to results file
    with open(POLICY_RESULTS_JSON, 'a') as policy_results_json:
        out_object = {dir_name: {
            'set_policy': set_policy,
            '1st_party_req': req_pol_1stparty,
            '3rd_party_req': req_pol_3rdparty,
            '3rd_party_resp': resp_pol_3rdparty
        }}
        json.dump(out_object, policy_results_json, indent=4)
print(sanity_check)
