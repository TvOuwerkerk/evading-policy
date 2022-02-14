import glob
import os
import json
import csv

DATA_PATH = os.path.join('Corpus-crawl')
CSV_RESULTS_FILE = os.path.join('results.csv')
TRANCO_LIST_FILE = os.path.join('Tranco-P99J-202107.csv')
DOMAIN_MAP_FILE = os.path.join('TR_domain_map.json')


def get_data_path():
    return DATA_PATH


def get_csv_results_file():
    return CSV_RESULTS_FILE


def get_tranco_ranking():
    with open(TRANCO_LIST_FILE, 'r') as tranco:
        output = []
        for row in csv.reader(tranco):
            output.append(row[0])
        return output


def get_corpus():
    corpus_path = glob.glob('Corpus')[0]
    with open(corpus_path, 'r') as corpus:
        return corpus.readlines()


def get_domain_map_file():
    with open(DOMAIN_MAP_FILE, encoding='utf-8') as domains:
        return json.load(domains)


def get_data_dirs(data_path):
    """
    Get a list of 'data.*' folders located in the folder pointed to by data_path
    """
    return [x for x in os.listdir(data_path) if x.startswith('data.')]


def get_data_files(directory_path: str, first_party=True):
    """
    Get a list of files containing crawled data in the data-folder pointed to by directory_path
    """
    data_files = [x for x in glob.glob(os.path.join(directory_path, '*.json')) if
                  not (x.startswith(os.path.join(directory_path, 'links'))
                       or x.startswith(os.path.join(directory_path, 'admin'))
                       or x.startswith(os.path.join(directory_path, 'metadata')))]
    if first_party:
        admin_file = os.path.basename(get_admin_file(directory_path))
        crawled_domain = admin_file[6:-5]
        for file in data_files:
            if crawled_domain not in os.path.basename(file):
                data_files.remove(file)
    return data_files


def get_links_files(directory_path: str):
    """
    Get a list of links. files containing scraped links, in the data-folder pointed to by directory_path
    """
    return glob.glob(os.path.join(directory_path, 'links.*.json'))


def get_log_files(directory_path):
    """
    Get a list of log files in the folder pointed to by directory_path
    """
    return glob.glob(os.path.join(directory_path, '*.log'))


def get_admin_file(directory_path):
    """
    Get the 'admin.*' file located in the folder pointed to by directory_path
    """
    return glob.glob(os.path.join(directory_path, 'admin.*.json'))[0]


def save_data_to_admin(file_data, admin_directory):
    """
    Saves given data to the admin-file found in the given directory
    :param admin_directory: directory in which admin-file is located
    :param file_data: data that needs to be added to results object in admin-file
    :return: None
    """
    admin_file_path = get_admin_file(admin_directory)
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
