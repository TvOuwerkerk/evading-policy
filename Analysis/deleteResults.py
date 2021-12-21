import json
import os
import glob


DATA_PATH = os.path.join('sampledata3')

data_directories = [x for x in os.listdir(DATA_PATH) if x.startswith('data.')]
for directory in data_directories:
    admin_directory = os.path.join(DATA_PATH, directory)
    admin_file_path = os.path.join(admin_directory, 'admin.*.json')[0]
    with open(admin_file_path, 'r+') as admin:
        admin_data = json.load(admin)
        try:
            admin_data['results'] = []
        except KeyError:
            continue
        admin.seek(0)
        json.dump(admin_data, admin, indent=4)
        admin.truncate()
