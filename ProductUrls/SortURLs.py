import json
import numpy as np
import pickle
import glob
import urllib.parse as parse
import re
import os
import warnings
warnings.filterwarnings('ignore', '.*SGDClassifier.*')

DATA_FOLDER = os.path.join('Prototype-crawl')
MODEL_PATH = os.path.join('models', 'log-reg-mod.pkl')

ACCEPTABLE_PROBABILITY = 0.5
NR_DESIRED_LINKS = 10


def get_url_path(url: str):
    """
    This function takes a URL and isolates everything after the '/' after the domain (i.e. path, queries and anchor)
    :param url: a URL given as string
    :return: portion of the URL that represents path, queries and anchor
    """
    parts = parse.urlsplit(url)
    if parts.netloc == '':
        raise ValueError(f'Invalid URL encountered: {url}')
    stripped_parts = parts._replace(scheme='', netloc='')
    return parse.urlunsplit(stripped_parts)


def get_longest_num_len(string: str):
    """
    Given a string, returns the length of the longest numerical sequence found within this string.
    """
    seqs = re.findall(r'(?:\d+)', string)
    if not seqs:
        return 0
    return len(max(seqs, key=len))


def get_url_features(url: str):
    """
    Extracts, from a given URL, the features needed to use the sklearn model to determine whether it's a product page
    """
    path = get_url_path(url)
    path_len = len(path)
    num_dot = path.count('.')
    num_hyphen = path.count('-')
    num_slash = path.count('/')
    num_hash = path.count('#')
    num_param = path.count('=')
    contains_product = 1 if any(tag in url for tag in ['product', 'produkt', 'item']) else 0
    contains_category = 1 if any(tag in url for tag in ['category', 'categorie', 'collection', 'collectie']) else 0
    longest_num = get_longest_num_len(url)
    return path_len, num_dot, num_hyphen, num_slash, num_hash, num_param, \
           contains_product, contains_category, longest_num


def get_prod_likelihoods(urllist: [str]) -> dict:
    """
    Calculates probabilities of a URL being link to a product page, for a list of URLs
    :param urllist: List of URLs as strings
    :return: A dict with key=url, value=probability
    """
    feature_list = []
    for url in urllist:
        feature_list.append(get_url_features(url))
    feature_array = np.asarray(feature_list)
    model_path = MODEL_PATH
    clf = pickle.load(open(model_path, 'rb'))
    proba = clf.predict_proba(feature_array)
    return dict(zip(urllist, proba[:, 1]))


def write_log(text: str):
    log_location = DATA_FOLDER
    log_path = glob.glob(os.path.join(log_location, '*.log'))[0]
    with open(log_path, 'a') as log:
        log.write(text)


def rename_log():
    log_location = DATA_FOLDER
    log_file_paths = glob.glob(os.path.join(log_location, '*.log'))
    log_path = [x for x in log_file_paths if not os.path.split(x)[1].startswith('_')][0]
    log_name = os.path.split(log_path)[1]
    os.rename(log_path, os.path.join(log_location, f'_{len(log_file_paths)}_{log_name}'))


dataDirectories = [x for x in os.listdir(DATA_FOLDER) if x.startswith('data.')]
files = []
# For every links-file in every data-directory, get the list of scraped urls and get probabilities
for directory in dataDirectories:
    directory_path = os.path.join(DATA_FOLDER, directory)
    prob_dicts = []
    files = glob.glob(os.path.join(directory_path, 'links.*.json'))
    for file in files:
        with open(file, 'r') as inp:
            url_list = list(set(json.load(inp)['internal']))
            if not url_list:
                continue
            prob_dicts.append(get_prod_likelihoods(url_list))

    # After tagging all gathered links in a specific data-directory, save the results to the admin-file
    admin_file = glob.glob(os.path.join(directory_path, 'admin.*'))[0]
    with open(admin_file, 'r+') as admin:
        administration: dict = json.load(admin)
        to_crawl: dict[str, int] = administration['tocrawl']
        visited: dict[str, int] = administration['visited']

        for dictionary in prob_dicts:
            for k in dictionary:
                if k in visited.keys():
                    continue
                to_crawl.update({k: dictionary[k]})
        to_crawl_sorted = sorted(list(to_crawl.items()), key=lambda x: x[1])
        to_crawl = dict(to_crawl_sorted[-NR_DESIRED_LINKS:])
        if len(to_crawl_sorted) < 10:
            write_log(f'{os.path.split(admin_file)[1]} contains less than 10 links\n')

        administration['tocrawl'] = to_crawl
        admin.seek(0)
        json.dump(administration, admin, indent=4)
        admin.truncate()
rename_log()
