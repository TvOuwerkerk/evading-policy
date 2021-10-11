import time
import random
import logging
import regex

from csv import reader
from csv import writer
from multiprocessing import Pool, Lock

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from webdriver_manager.firefox import GeckoDriverManager

import pycld2
from polyglot.detect import Detector
from polyglot.detect.base import UnknownLanguage

driver_path = GeckoDriverManager().install()
options = webdriver.FirefoxOptions()
options.headless = True

timestamp = time.strftime('%d-%b-%Y_%H%M', time.localtime())
logname = 'LanguageTagging_' + timestamp + '.log'
logging.basicConfig(filename=logname, level=logging.INFO)

RE_BAD_CHARS = regex.compile(r"\p{Cc}|\p{Cs}")


# Sanitation code provided by:
# https://github.com/mikemccand/chromium-compact-language-detector/issues/22#issuecomment-707999784
def remove_bad_chars(text):
    return RE_BAD_CHARS.sub("", text)


def get_lan_code(text):
    if text == '':
        return 'Empty'

    detector = Detector(text)
    if detector.language.confidence >= 0.9 and detector.reliable:
        return detector.language.code
    return 'Unreliable'


def get_inner_text(driver):
    return driver.execute_script('return (!!document.body && document.body.innerText)')


def get_text(site, driver):
    logging.info(' - Retrieving - ' + site)
    driver.get(site)
    if driver.current_url != site:
        logging.info(' - Retrieving: Redirect detected - {0} TO {1}'.format(site, driver.current_url))
    time.sleep(5)
    text = get_inner_text(driver)
    if text == '':
        time.sleep(5)
        logging.info(' - Retrieving: Retry - ' + site)
        text = get_inner_text(driver)
    if text == '':
        logging.warning(' - Retrieving: Empty text - ' + site)
        return None
    return 0, text


def tag_row(row):
    driver = webdriver.Firefox(executable_path=driver_path, firefox_options=options)
    try:
        return_code, value = get_text(row[0], driver)
        driver.quit()
    except TimeoutException:
        logging.exception(' - Retrieving: Timeout - ' + row[0])
        return
    except Exception as exc:  # Catch problems like CAPTCHA or broken websites
        # TODO: Catch specific exceptions that can occur during retrieval.
        logging.exception('- Retrieving - ' + row[0])
        driver.quit()
        return
    if return_code is None:
        return

    try:
        lan_code = get_lan_code(value)
    except pycld2.error:
        logging.warning(' - Retrieving: Unicode error, retrying - ' + row[0])
        lan_code = get_lan_code(remove_bad_chars(value))
    except UnknownLanguage:
        lan_code = 'Unknown'
    except Exception:  # Catch unexpected problems in detecting languages
        # TODO: Catch specific exceptions that can occur during tagging.
        logging.exception('- Tagging - ' + row[0])
        driver.quit()
        return
    if lan_code == 'Empty':
        logging.error('Tagging: Empty text - ' + row[0])
        return
    if lan_code in ['Unknown', 'un', '']:
        logging.error('Tagging: Unknown language - ' + row[0])
        return
    if lan_code == 'Unreliable':
        logging.error('Tagging: Low confidence - ' + row[0])
        return

    row = [row[0]] + [lan_code] + row[1:]
    with Lock():
        with open('CRUX-McAfee-Cat_Lan.csv', 'a', newline='') as tagged:
            csv_writer = writer(tagged)
            csv_writer.writerow(row)


if __name__ == '__main__':
    logging.info('Current time: ' + time.strftime('%d-%b-%Y_%H%M', time.localtime()))
    nr_runners = 8
    sample_size = 0
    with open('CRUX-McAfee-Cat.csv', 'r', newline='') as read_obj:
        inp_list = [x for x in list(reader(read_obj)) if x is not None]
        if sample_size <= 0:
            to_tag = inp_list
        else:
            to_tag = random.sample(inp_list, sample_size)
        with Pool(nr_runners) as pool:
            pool.map(tag_row, to_tag)
    logging.info('Current time: ' + time.strftime('%d-%b-%Y_%H%M', time.localtime()))
