import glob
import os
import json
import csv

DATA_PATH = os.path.join('Corpus-crawl')
CSV_RESULTS_FILE = os.path.join('results.csv')
JSON_POLICY_RESULTS_FILE = os.path.join('policy_results.json')
TRANCO_LIST_FILE = os.path.join('Tranco-P99J-202107.csv')
DOMAIN_MAP_FILE = os.path.join('TR_domain_map.json')


def get_data_path():
    return DATA_PATH


def get_csv_results_file():
    return CSV_RESULTS_FILE


def get_policy_results_file():
    return JSON_POLICY_RESULTS_FILE


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


def get_data_dirs():
    """
    Get a list of 'data.*' folders located in the folder pointed to by data_path
    """
    return [x for x in os.listdir(DATA_PATH) if x.startswith('data.')]


def get_data_files(directory_name: str, first_party=True):
    """
    Get a dict with total list and valid list of files containing crawled data in the data-folder named directory_name
    :param directory_name: name of the folder in which the data files should be found
    :param first_party: if True, data files with a differing domain in the filename from the folder get filtered out.
    :return: dict with 2 entries: 'total' being a list of all data files, 'valid' containing the same list if
    first_party is False, or a filtered version of 'total' if first_party is True.
    """
    directory_path = os.path.join(DATA_PATH, directory_name)

    total_data_files = [x for x in glob.glob(os.path.join(directory_path, '*.json')) if
                        not (x.startswith(os.path.join(directory_path, 'links'))
                        or x.startswith(os.path.join(directory_path, 'admin'))
                        or x.startswith(os.path.join(directory_path, 'metadata')))]

    admin_file = os.path.basename(get_admin_file(os.path.basename(directory_path)))
    crawled_domain = admin_file[6:-5]
    if first_party:
        valid_data_files = [f for f in total_data_files if crawled_domain in os.path.basename(f)]
    else:
        valid_data_files = total_data_files
    return {'total': total_data_files, 'valid': valid_data_files}


def get_links_files(directory_name: str):
    """
    Get a list of links. files containing scraped links, in the data-folder with name directory_name
    """
    directory_path = os.path.join(DATA_PATH, directory_name)
    return glob.glob(os.path.join(directory_path, 'links.*.json'))


def get_log_files():
    """
    Get a list of log files in the main crawl-data folder
    """
    return glob.glob(os.path.join(DATA_PATH, '*.log'))


def get_admin_file(directory_name: str):
    """
    Get the 'admin.*' file located in the data-folder with name directory_name
    """
    directory_path = os.path.join(DATA_PATH, directory_name)
    return glob.glob(os.path.join(directory_path, 'admin.*.json'))[0]


def save_data_to_admin(file_data, admin_directory):
    """
    Saves given data to the admin-file found in the given directory
    :param admin_directory: name of the directory in which admin-file is located
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
