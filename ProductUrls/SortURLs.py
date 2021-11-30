import json
import numpy as np
import pickle
import glob
import urllib.parse as parse
import re

ACCEPTABLE_PROBABILITY = 0.5


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

    clf = pickle.load(open('.\\models\\log-reg-mod.pkl', 'rb'))
    proba = clf.predict_proba(feature_array)
    return dict(zip(urllist, proba[:, 1]))


files = glob.glob('sampleData\\links.*.json')
for file in files:
    domain = file.split('_')[0][6:]
    admin_file = f'sampleData\\admin.{domain}.json'

    with open(file, 'r') as inp, open(admin_file, 'r+') as admin:
        url_list = list(set(json.load(inp)['internal']))
        prob_dict = get_prod_likelihoods(url_list)

        administration = json.load(admin)
        todo = set(administration['todo'])
        visited = set(administration['visited'])

        for x in prob_dict.items():
            if x[1] < ACCEPTABLE_PROBABILITY:
                continue
            if x[0] in visited:
                continue
            todo.add(x[0])

        administration['todo'] = list(todo)
        admin.seek(0)
        json.dump(administration, admin, indent=4)
        admin.truncate()


