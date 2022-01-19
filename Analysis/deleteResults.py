import json
import os
from tqdm import tqdm
import fileUtils

DATA_PATH = fileUtils.get_data_path()
RESULTS_CSV = fileUtils.get_csv_results_file()

data_directories = fileUtils.get_data_dirs(DATA_PATH)
for directory in tqdm(data_directories):
    admin_directory = os.path.join(DATA_PATH, directory)
    admin_file_path = fileUtils.get_admin_file(admin_directory)
    with open(admin_file_path, 'r+', encoding='utf-8') as admin:
        admin_data = json.load(admin)
        try:
            admin_data['results'] = []
        except KeyError:
            continue
        admin.seek(0)
        json.dump(admin_data, admin, indent=4)
        admin.truncate()
open(RESULTS_CSV, 'w').close()
