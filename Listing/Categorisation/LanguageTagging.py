import time
from csv import reader
from csv import writer

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from webdriver_manager.firefox import GeckoDriverManager
from polyglot.detect import Detector
from polyglot.detect.base import UnknownLanguage
from tqdm import tqdm

driver_path = GeckoDriverManager().install()
driver = webdriver.Firefox(executable_path=driver_path)


def get_lan_code(text):
    code = ''
    text_bits = [text]
    if text == '':
        return 'Empty'
    x = 0
    while code == '' and x < 5:
        start_len_bits = len(text_bits)
        for y in range(start_len_bits):
            piece = text_bits[y]
            try:
                detector = Detector(text)
                if detector.reliable:
                    return detector.language.code
            except UnknownLanguage:
                x += 1
                text_bits.append(piece[:len(piece)])
                text_bits[text_bits.index(piece)] = piece[len(piece):]

    # return language with highest confidence level, unless 'nl' or 'en' is present with high enough confidence


with open('BigQuery-McAfee-Cat.csv', 'r') as read_obj, open('BigQuery-McAfee-Cat_Lan.csv', 'w') as tagged:
    csv_reader = reader(read_obj)
    csv_writer = writer(tagged)
    for row in tqdm(csv_reader):
        # Download webpage text
        try:
            driver.get(row[0])
        except TimeoutException:
            with open('Lan-tagging_errors.csv', 'a') as errors:
                errors.write(row[0] + " Retrieval timeout\n")
            continue
        text = driver.find_element_by_xpath('/html/body').text
        if text == '':
            time.sleep(2)
            text = driver.find_element_by_xpath('/html/body').text
        if text == '':
            with open('Lan-tagging_errors.csv', 'a') as errors:
                errors.write(row[0] + " Empty text\n")
            continue
        # Use polyglot to get language tag
        lan_code = get_lan_code(text)
        if lan_code == 'Empty':
            with open('Lan-tagging_errors.csv', 'a') as errors:
                errors.write(row[0] + " Empty text\n")
            continue
        if lan_code in ['Unknown', 'un', '']:
            with open('Lan-tagging_errors.csv', 'a') as errors:
                errors.write(row[0] + " Unknown language\n")
            continue
        row = [row[0]] + [lan_code] + row[1:]
        row[-1] = row[-1].strip()
        csv_writer.writerow(row)
    driver.close()
