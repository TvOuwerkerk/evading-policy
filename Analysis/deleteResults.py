import json
import os
import glob


DATA_PATH = '.\\sampledata2'

data_directories = [x for x in os.listdir(DATA_PATH) if x.startswith('data.')]
files = []
for directory in data_directories:
    admin_directory = f'{DATA_PATH}\\{directory}'
    admin_file_path = glob.glob(f'{admin_directory}\\admin.*.json')[0]
    with open(admin_file_path, 'r+') as admin:
        admin_data = json.load(admin)
        try:
            admin_data['results'] = []
        except KeyError:
            continue
        admin.seek(0)
        json.dump(admin_data, admin, indent=4)
        admin.truncate()
