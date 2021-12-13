import json
import os
import glob
import urllib.parse as parse
import hashlib

DATA_PATH = '.\\slice'


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

    search_dict = {"source": source,
                   "path": path,
                   "schemeless": schemeless_source,
                   "source percent": parse.quote(source),
                   "path percent": parse.quote(path),
                   "schemeless percent": parse.quote(schemeless_source),
                   "source md5": hashlib.md5(source.encode('utf-8')),
                   "path md5": hashlib.md5(path.encode('utf-8')),
                   "schemeless md5": hashlib.md5(schemeless_source.encode('utf-8')),
                   "source sha1": hashlib.sha1(source.encode('utf-8')),
                   "path sha1": hashlib.sha1(path.encode('utf-8')),
                   "schemeless sha1": hashlib.sha1(schemeless_source.encode('utf-8'))}
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
