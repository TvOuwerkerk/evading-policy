import requests
import json
import time
from tqdm import tqdm

url='https://api.builtwith.com/free1/api.json?KEY=3f3863d3-56be-4f7e-8154-56fafd20200b&LOOKUP={}'

with open('BigQuery-Top170k-NL-clean.csv','r') as inp:
    lines = inp.readlines()

for line in tqdm(lines):
    response = requests.get(url.format(line))
    data = json.loads(response.content.decode())    
    if data.get('errors',[]):
        print('Error:' + line)
    for group in data.get('groups', []):
         if group['name'] in ['ecommerce','payment','shipping']:
            with open('BigQuery-NL-ECommerce.csv','a') as out:
                out.write(line)
                print('Found one! Group {} on {}'.format(group['name'],line))
                break
    time.sleep(1)
