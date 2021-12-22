import json
import os
import glob
import urllib.parse as parse
import hashlib
import base64
from tqdm import tqdm

DATA_PATH = os.path.join('Corpus-Head-crawl')


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
        schemeless[x] = parse.urlunsplit(parse.urlsplit(x)._replace(scheme=''))
        fragmentless[x] = parse.urlunsplit(parse.urlsplit(x)._replace(fragment='', scheme=''))

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


def check_url_leakage(leaked_url, alternate_leaked_url, target_url):
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
    split_request_url = parse.urlsplit(target_url)
    if crawled_domain == split_request_url.netloc or redirected_domain == split_request_url.netloc:
        return None
    # Same thing, but urllib has trouble dealing with 'blob:' urls, so we check for that case here
    if split_request_url.netloc == '' and parse.urlsplit(split_request_url.path).netloc == crawled_domain:
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


def save_data_to_admin(file_data, admin_directory):
    """
    Saves given data to the admin-file found in the given directory
    :param admin_directory: directory in which admin-file is located
    :param file_data: data that needs to be added to results object in admin-file
    :return: None
    """
    admin_file_path = glob.glob(os.path.join(admin_directory, 'admin.*.json'))[0]
    with open(admin_file_path, 'r+', encoding='utf-8') as admin:
        admin_data = json.load(admin)
        try:
            admin_data['results'].append(file_data)
        except KeyError:
            admin_data['results'] = []
            admin_data['results'].append(file_data)
        admin.seek(0)
        json.dump(admin_data, admin, indent=4)
        admin.truncate()


def file_is_crawled_data(filename: str):
    return not (filename.startswith(os.path.join(directory_path, 'links'))
                or filename.startswith(os.path.join(directory_path, 'admin'))
                or filename.startswith(os.path.join(directory_path, 'metadata')))


# Find all directories which have data saved to them
data_directories = [x for x in os.listdir(DATA_PATH) if x.startswith('data.')]
files = []
directories_progress = tqdm(data_directories)
for directory in directories_progress:
    # Create object to save results into
    results = []
    # Find all .json files that contain crawled data
    directory_path = os.path.join(DATA_PATH, directory)
    files = [x for x in glob.glob(os.path.join(directory_path, '*.json')) if file_is_crawled_data(x)]
    for file in files:
        with open(file, encoding='utf-8') as data_file:
            # Load the data gathered from a page visit
            data: dict = json.load(data_file)

            # Get the requests gathered and url visited
            requests = list(data['data']['requests'])
            crawled_url = data['initialUrl']
            redirected_url = data['finalUrl']

            # Create file_results object, containing all results that need to be saved to the admin-file later
            file_results = {'crawled-url': crawled_url,
                            'redirected-url': '',
                            'referrer-policy': '',
                            'referrer-policy-set': False,
                            'request-leakage': []}

            if crawled_url != redirected_url:
                file_results['redirected-url'] = redirected_url

            for request in requests:
                request_url = request['url']

                if request_url == crawled_url:
                    if 'responseHeaders' in request and 'referrer-policy' in request['responseHeaders']:
                        referrer_policy = request['responseHeaders']['referrer-policy']
                        file_results['referrer-policy'] = referrer_policy
                        file_results['referrer-policy-set']: True
                    else:
                        file_results['referrer-policy'] = request['referrerPolicy']

                result = check_url_leakage(crawled_url, redirected_url, request_url)
                if result is not None:
                    file_results['request-leakage'].append(result)

        # Remove items for which values have not been set
        file_results = {k: v for k, v in file_results.items() if v}
        save_data_to_admin(file_results, directory_path)
