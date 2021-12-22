import json
import os
import glob
import urllib.parse as parse


DATA_PATH = '.\\Corpus-Head-crawl'
UNSAFE_POLICIES = ['unsafe-url', 'no-referrer-when-downgrade']
SAFE_POLICIES = ['no-referrer', 'origin', 'origin-when-cross-origin',
                 'same-origin', 'strict-origin', 'strict-origin-when-cross-origin']

# TODO: split code into functions for better readability of main code
# TODO: consider leakage from non-front page URLs as more interesting printable result
data_directories = [x for x in os.listdir(DATA_PATH) if x.startswith('data.')]
for directory in data_directories:
    admin_directory = f'{DATA_PATH}\\{directory}'
    admin_file_path = glob.glob(f'{admin_directory}\\admin.*.json')[0]
    with open(admin_file_path, 'r') as admin:
        admin_data = json.load(admin)
        # Get results of all pages on this domain
        try:
            results = admin_data['results']
        except KeyError:
            print(f'No results in: {admin_file_path}')
            continue

        encountered_policies = set()
        encountered_leakage = set()
        # Consider results of all crawled pages on this domain
        for r in results:
            crawled_domain = parse.urlsplit(r['crawled-url']).netloc
            try:
                referrer_policy = r["referrer-policy"]
            except KeyError:
                continue

            # If the crawled page uses a referrer-policy that has not been seen on this domain, check if it's unsafe
            if referrer_policy not in encountered_policies:
                encountered_policies.add(referrer_policy)
                if referrer_policy in UNSAFE_POLICIES:
                    # TODO: report if this is global policy or something specific for this request
                    print(f'{crawled_domain} uses unsafe referrer-policy {referrer_policy}')

            # If the crawled page uses a safe referrer-policy, there's a chance this is being circumvented
            if referrer_policy in SAFE_POLICIES and r['request-leakage']:
                current_leakage = set()
                # Consider all cases of leakage occurring on this page
                for request in r['request-leakage']:
                    domain = parse.urlsplit(request['request-url']).netloc
                    # If leakage on this page occurs to a domain we've already encountered on a different page, continue
                    if domain in encountered_leakage:
                        continue
                    # If we've found a new leak destination, add it to overall encountered and encountered for this page
                    encountered_leakage.add(domain)
                    current_leakage.add(domain)
                # If we encountered any leakage on this specific page, print accordingly
                if current_leakage:
                    print(f'{crawled_domain} circumvents policy \"{referrer_policy}" and leaks to:')
                    for leak in current_leakage:
                        if not leak.startswith('www'):
                            leak = f'www.{leak}'
                        print(f'\t{leak}')
