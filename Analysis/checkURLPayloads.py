import json
import os
import glob
import urllib.parse as parse
import hashlib

DATA_PATH = '.\\slice'


def encode_search_dict(to_search: dict, encoding, encoding_name: str):
    keys = map(lambda a: f'{a}-{encoding_name}', to_search.keys())
    values = map(encoding, to_search.values())
    return dict(zip(keys, values))


def check_url_in_url(source: str, target: str):
    """
    Searches a target URL for occurences of (parts of) the source URL in several encodings.
    :param source: URL that needs to be searched for
    :param target: URL that needs to be searched through
    :return: True if (a part of) the source URL is found, False otherwise
    """

    path = parse.urlsplit(source).path
    path_present = True
    if path == '/':
        path_present = False

    schemeless_split = parse.urlsplit(source)
    schemeless_split.scheme = ''
    schemeless_source = parse.urlunsplit(schemeless_split)

    encodings = []
    search_dict = {}
    to_search_dict = {"source": source,
                      "path": path,
                      "schemeless": schemeless_source}
    search_dict.update(to_search_dict)
    encodings.append(to_search_dict)
    encodings.append(encode_search_dict(to_search_dict, parse.quote, 'percent'))
    encodings.append(encode_search_dict(to_search_dict, lambda a: hashlib.md5(a.encode('utf-8')), 'md5'))
    encodings.append(encode_search_dict(to_search_dict, lambda a: hashlib.sha1(a.encode('utf-8')), 'sha1'))

    for dictionary in encodings:
        search_dict.update(dictionary)
    # TODO: base64 encoding

    for x in search_dict.keys():
        if x.startswith('path') and not path_present:
            continue
        if str(search_dict[x]) in target:
            return x
    return ""


dataDirectories = [x for x in os.listdir(DATA_PATH) if x.startswith('data.')]
dataDirectories.append(DATA_PATH)
files = []
for directory in dataDirectories:
    # Find all .json files that are not a links. or admin. file
    files = [x for x in glob.glob(f'{directory}\\*.json') if not (x.startswith(f'{directory}\\links')
             or x.startswith(f'{directory}\\admin') or x.startswith(f'{directory}\\metadata'))]
    for file in files:
        with open(file) as data_file:
            data: dict = json.load(data_file)
            if data['initialUrl'] != data['finalUrl']:
                print(f'{file}: Crawl was redirected')

            requests = list(data['data']['requests'])
            crawled_url = data['initialUrl']
            crawled_domain = parse.urlsplit(crawled_url).netloc
            for request in requests:
                request_url = request['url']

                # If the current request is to a 1st party domain, skip it
                if crawled_domain == parse.urlsplit(request_url).netloc:
                    continue

                # Check if (parts of) the crawled url appear in the request url
                check = check_url_in_url(crawled_url, request_url)
                if check != "":
                    print(f'{file}: Found {check} in {request_url}')
