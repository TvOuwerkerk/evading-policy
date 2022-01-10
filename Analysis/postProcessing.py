import json
import os
import glob
import urllib.parse as parse
import hashlib
import base64
from tqdm import tqdm
from sanityCheck import SanityCheck
import fileUtils

DATA_PATH = os.path.join('Corpus-crawl')
UNSAFE_POLICIES = ['unsafe-url', 'no-referrer-when-downgrade']
SAFE_POLICIES = ['no-referrer', 'origin', 'origin-when-cross-origin',
                 'same-origin', 'strict-origin', 'strict-origin-when-cross-origin']


def is_request_url_third_party(page_url: str, alternate_page_url: str, request_url: str):
    split_request_url = parse.urlsplit(request_url)
    if page_url == split_request_url.netloc or alternate_page_url == split_request_url.netloc:
        return False
    # Same thing, but urllib has trouble dealing with 'blob:' urls, so we check for that case here
    if split_request_url.netloc == '' and parse.urlsplit(split_request_url.path).netloc == page_url:
        return False
    return True


def encode_search_dict(to_search: dict[str, str], encoding, encoding_name: str):
    """
    Encodes values and changes keys accordingly for a given dict
    :param to_search: dict containing keyed strings that need to be searched for
    :param encoding: function that encodes a given str
    :param encoding_name: encoding name that is added to keys of to_search dict
    :return: dict containing changed keys and encoded values
    """
    keys = map(lambda a: f'{a}-{encoding_name}', to_search.keys())
    values = map(encoding, to_search.values())
    return dict(zip(keys, values))


def check_url_in_url(source: str, alternate_source: str, target: str):
    """
    Searches a target URL for occurrences of (parts of) the source URL in several encodings.
    :param source: URL that needs to be searched for
    :param alternate_source: Alternate version of URL that needs to be searched for (in case of redirect)
    :param target: URL that needs to be searched through
    :return: True if (a part of) the source or alternate URL is found, False otherwise
    """
    inp = {'source': source, 'alternate': alternate_source}
    path, path_present, schemeless, fragmentless = ({},) * 4
    for x in ['source', 'alternate']:
        path[x] = parse.urlsplit(inp[x]).path
        path_present[x] = False
        if path[x] == '/':
            path_present[x] = False
        schemeless[x] = strip_scheme(x)
        fragmentless[x] = strip_scheme_and_fragment(x)

    encodings = []
    search_dict = {}
    to_search_dict = {'source': source,
                      'redirected': alternate_source,
                      'source_path': path['source'],
                      'redirected_path': path['alternate'],
                      'source_schemeless': schemeless['source'],
                      'redirected_schemeless': schemeless['alternate'],
                      'source_fragmentless': fragmentless['source'],
                      'redirected_fragmentless': fragmentless['alternate']}
    search_dict.update(to_search_dict)
    encodings.append(to_search_dict)
    encodings.append(encode_search_dict(to_search_dict, lambda a: parse.quote(a, safe=''), 'percent'))
    encodings.append(encode_search_dict(to_search_dict, lambda a: hashlib.md5(a.encode('utf-8')), 'md5'))
    encodings.append(encode_search_dict(to_search_dict, lambda a: hashlib.sha1(a.encode('utf-8')), 'sha1'))
    encodings.append(encode_search_dict(to_search_dict, lambda a: base64.urlsafe_b64encode(bytes(a, 'utf-8')), 'base64'))

    for dictionary in encodings:
        search_dict.update(dictionary)

    for x in search_dict.keys():
        if x.startswith('source-path') and not path_present['source']:
            continue
        if x.startswith('redirected-path') and not path_present['alternate']:
            continue
        if str(search_dict[x]) in target:
            return x
    return ''


def check_url_leakage(leaked_url: str, alternate_leaked_url: str, target_url: str):
    """
    Check whether (part of) a given URL is leaked in the target URL
    :param leaked_url: URL which is potentially (partially) leaked
    :param alternate_leaked_url: Alternate URL which is potentially (partially) leaked
    :param target_url: URL in which (part of) leaked_url could be found
    :return: None if no leakage is found. Dict containing target url, part found and encoding used if leakage is found
    """
    crawled_domain = parse.urlsplit(leaked_url).netloc
    redirected_domain = parse.urlsplit(alternate_leaked_url).netloc

    # If the current request is to a 1st party domain, skip it
    if not is_request_url_third_party(crawled_domain, redirected_domain, target_url):
        return None

    # Check if (parts of) the crawled url appear in the request url
    check = check_url_in_url(leaked_url, alternate_leaked_url, target_url)
    if check != '':
        try:
            encoding = check.split('-')[1]
        except IndexError:
            encoding = 'none'
        request_result = {'request-url': target_url,
                          'part-found': check.split('-')[0],
                          'encoding': encoding}
        return request_result
    return None


def check_unsafe_policy(page_url: str, alternate_page_url: str, request_data: dict):
    # If the current request is to a 1st party domain, skip it
    if not is_request_url_third_party(page_url, alternate_page_url, request_data['url']):
        return None
    request_result = {'request-url': request_data['url'],
                      'request-referrer-policy': ''}
    request_policy = request_data['referrerPolicy']
    if (request_policy == 'no-referrer-when-downgrade' and parse.urlparse(request_data['url']).scheme == 'http')\
            or request_policy == 'unsafe-ur':
        request_result['referrer-policy'] = request_policy
        if 'responseHeaders' in request_data and 'referrer-policy' in request_data['responseHeaders']:
            response_policy = request_data['responseHeaders']['referrer-policy']
            if response_policy == request_policy:
                request_result['equal-to-response'] = True
            else:
                request_result['equal-to-response'] = False
        return request_result
    return None


def find_cmp_occurrences_in_logs():
    log_files = fileUtils.get_log_files(DATA_PATH)
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


def get_request_info(request_data: dict, file_results: dict, request_source: str, alt_request_source: str):
    """
    Takes a request as dictionary and adds inferred data to the file_results dictionary.
    Sets 'referrer-policy' and 'referrer-policy-set' fields if this request is made to (alt_)request_source
    Adds request to 'request-leakage' list if this request leaked info on the (alt_)request_source
    Adds request to 'unsafe-outbound' list of request was made to third party using an unsafe referrer-policy
    :param request_data: dictionary containing the data of the request
    :param file_results: dictionary to which data about the request must be saved
    :param request_source: url from which the request was made
    :param alt_request_source: alternate (possibly redirected) url from which the request was made
    :return:
    """
    request_url = request_data['url'].strip('/')
    request_source = request_source.strip('/')
    alt_request_source = alt_request_source.strip('/')

    request_ref_policy = request_data['referrerPolicy']
    try:
        response_ref_policy = request_data['responseHeaders']['referrer-policy']
    except KeyError:
        response_ref_policy = ''

    # If we hold the main request to the crawled url, set check if page-wide policy is set
    if request_url == request_source or request_url == strip_fragment(request_source)\
            or request_url == alt_request_source or request_url == strip_fragment(alt_request_source):
        if response_ref_policy:
            file_results['referrer-policy'] = response_ref_policy
            file_results['referrer-policy-set'] = True
        else:
            file_results['referrer-policy'] = request_ref_policy
    # If we do not hold the main request, we can assume the referrer-policy has been set, if this page does so
    else:
        if response_ref_policy:
            if request_ref_policy in UNSAFE_POLICIES and response_ref_policy in SAFE_POLICIES:
                downgrade_result = {'request-url': request_url,
                                    'request-policy': request_ref_policy,
                                    'response-policy': response_ref_policy}
                file_results['downgrade-policy'].append(downgrade_result)

    leakage_result = check_url_leakage(request_source, alt_request_source, request_data['url'])
    if leakage_result is not None:
        file_results['request-leakage'].append(leakage_result)

    unsafe_result = check_unsafe_policy(request_source, alt_request_source, request_data)
    if unsafe_result is not None:
        file_results['unsafe-outbound'].append(unsafe_result)

    policy_used = response_ref_policy if response_ref_policy else request_ref_policy
    try:
        file_results['policies-used'][policy_used] += 1
    except KeyError:
        file_results['policies-used'][policy_used] = 1

    return file_results


def strip_fragment(url: str):
    return parse.urlunsplit(parse.urlsplit(url)._replace(fragment=''))


def strip_scheme(url: str):
    return parse.urlunsplit(parse.urlsplit(url)._replace(scheme=''))


def strip_scheme_and_fragment(url: str):
    return strip_scheme(strip_fragment(url))


# Find all directories which have data saved to them
data_directories = fileUtils.get_data_dirs(DATA_PATH)
files = []
cmp_lookup_dict = find_cmp_occurrences_in_logs()
sanity_check = SanityCheck()
for directory in tqdm(data_directories):
    sanity_check.incr_nr_dirs()
    # Create object to save results into
    results = []
    # Find all .json files that contain crawled data
    directory_path = os.path.join(DATA_PATH, directory)
    files = fileUtils.get_data_files(directory_path)
    sanity_check.add_to_page_counts(len(files))

    with open(glob.glob(os.path.join(directory_path, 'admin.*.json'))[0], 'r', encoding='utf-8') as admin_file:
        nr_visited = len(list(json.load(admin_file)['visited']))
        sanity_check.add_to_results_ratio(len(files), nr_visited)

    for file in files:
        with open(file, 'r', encoding='utf-8') as data_file:
            # Load the data gathered from a page visit
            data: dict = json.load(data_file)

            # Get the requests gathered and url visited
            try:
                requests = list(data['data']['requests'])
                if len(requests) == 0:
                    raise KeyError
            except KeyError:
                sanity_check.incr_requestless()
                continue
            crawled_url = parse.urlunparse(parse.urlparse(data['initialUrl']))
            redirected_url = data['finalUrl']
            # Create file_output object, containing all results that need to be saved to the admin-file later
            file_output = {'crawled-url': crawled_url,
                           'CMP-encountered': '',
                           'redirected-url': '',
                           'referrer-policy': '',
                           'referrer-policy-set': False,
                           'policies-used': {},
                           'request-leakage': [],
                           'unsafe-outbound': [],
                           'downgrade-policy': []}

            if parse.urlsplit(crawled_url).netloc != parse.urlsplit(redirected_url).netloc:
                continue

            if crawled_url != redirected_url:
                file_output['redirected-url'] = redirected_url

            if crawled_url in cmp_lookup_dict:
                file_output['CMP-encountered'] = cmp_lookup_dict[crawled_url]

            for request in requests:
                if request['type'] == 'WebSocket':
                    continue
                # file_output = get_request_info(request, file_output, crawled_url, redirected_url)

            # Remove items for which values have not been set
            file_output = {k: v for k, v in file_output.items() if v}
            # save_data_to_admin(file_output, directory_path)
print(sanity_check)

# TODO: consider cases where browser uses less strict policy than response indicates?
# TODO: count policies used only for 3rd-party requests? Wouldn't overcount unsafe policies if these are only applied to first party