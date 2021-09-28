import time
from csv import reader
from csv import writer
from multiprocessing import Pool, TimeoutError, Lock

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from webdriver_manager.firefox import GeckoDriverManager
from polyglot.detect import Detector
from polyglot.detect.base import UnknownLanguage
import random

driver_path = GeckoDriverManager().install()
options = webdriver.FirefoxOptions()
options.headless = True


def get_lan_code(text):
    if text == '':
        return 'Empty'
    try:
        detector = Detector(text)
        if detector.language.confidence >= 0.9 and detector.reliable:
            return detector.language.code
        return 'Unreliable'
    except UnknownLanguage:
        return 'Unknown'


def get_inner_text(driver):
    return driver.execute_script('return (!!document.body && document.body.innerText)')


def get_text(site, driver):
    print('getting ' + site)
    try:
        driver.get(site)
    except TimeoutException:
        print('Timeout reached getting: ' + site)
        return -1, [site] + [' Retrieval timeout\n']
    time.sleep(5)
    text = get_inner_text(driver)
    if text == '':
        print('Second attempt getting text for: ' + site)
        time.sleep(5)
        text = get_inner_text(driver)
    else:
        return 0, text
    if text == '':
        return -1, [site] + [' Empty text\n']


def tag_row(row):
    driver = webdriver.Firefox(executable_path=driver_path, firefox_options=options)
    try:
        return_code, value = get_text(row[0], driver)
        driver.quit()
    except Exception as exc:  # Catch problems like CAPTCHA or broken websites TODO: proper exception handling
        print(str(exc) + ' exception encountered in getting')
        print(row[0])
        driver.quit()
        return -1, [row[0]] + [str(exc)]
    if return_code == -1:
        return return_code, value
    try:
        lan_code = get_lan_code(value)
    except Exception as exc:  # Catch unexpected problems in detecting languages TODO: proper exception handling
        print(str(exc) + ' exception encountered in detecting')
        print(row[0])
        print(exc.args)
        return -1, [row[0]] + [str(exc)]
    if lan_code == 'Empty':  # TODO Replace following with error logging
        return -1, [row[0]] + ['Empty text\n']
    if lan_code in ['Unknown', 'un', '']:
        return -1, [row[0]] + ['Unknown language\n']
    if lan_code == 'Unreliable':
        return -1, [row[0]] + ['Low confidence\n']

    row = [row[0]] + [lan_code] + row[1:]
    with Lock():
        with open('CRUX-McAfee-Cat_Lan.csv', 'a', newline='') as tagged:
            csv_writer = writer(tagged)
            csv_writer.writerow(row)


if __name__ == '__main__':
    nr_runners = 4
    with open('CRUX-McAfee-Cat.csv', 'r', newline='') as read_obj, \
            open('Tagging-errors.csv', 'w', newline='') as errors:
        inp_list = [x for x in list(reader(read_obj)) if x is not None]
        csv_error_writer = writer(errors)
        inp = random.sample(inp_list, 10)
        with Pool(nr_runners) as pool:
            output = pool.map(tag_row, inp)

        for line in output:  # TODO: have output runner using shared queue (Note: threads may be more suitable)
            if line is None:
                continue
            if line[0] == -1:
                csv_error_writer.writerow(line[1])
                continue
            else:
                print('Invalid code found in output')
