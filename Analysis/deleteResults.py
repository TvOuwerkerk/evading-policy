import json
from tqdm import tqdm
import fileUtils

DATA_PATH = fileUtils.get_data_path()
RESULTS_CSV = fileUtils.get_csv_results_file()
POLICY_RESULTS_JSON = fileUtils.get_policy_results_file()

data_directories = fileUtils.get_data_dirs()
for directory in tqdm(data_directories):
    admin_file_path = fileUtils.get_admin_file(directory)
    with open(admin_file_path, 'r+', encoding='utf-8') as admin:
        try:
            admin_data = json.load(admin)
        except json.decoder.JSONDecodeError:
            print(f'JSONDecodeError encountered in admin file in {directory}')
            exit(-1)
        try:
            admin_data['results'] = []
        except KeyError:
            continue
        admin.seek(0)
        json.dump(admin_data, admin, indent=4)
        admin.truncate()
open(RESULTS_CSV, 'w').close()
open(POLICY_RESULTS_JSON, 'w').close()
