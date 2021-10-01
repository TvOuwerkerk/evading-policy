import time
import random
import logging
from csv import reader
from csv import writer
from multiprocessing import Pool, Lock

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from webdriver_manager.firefox import GeckoDriverManager

from polyglot.detect import Detector
from polyglot.detect.base import UnknownLanguage

driver_path = GeckoDriverManager().install()
options = webdriver.FirefoxOptions()
options.headless = True

timestamp = time.strftime('%d-%b-%Y_%H%M', time.localtime())
logname = 'LanguageTagging_' + timestamp + '.log'
logging.basicConfig(filename=logname, level=logging.INFO)


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
    # TODO:  log actual site being retrieved after any possible redirections
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
        logging.exception('- Retrieving - ' + row[0] + '\n' + str(exc))
        driver.quit()
        return
    if return_code is None:
        return

    try:
        lan_code = get_lan_code(value)
    except UnknownLanguage as unknown:
        lan_code = 'Unknown'
    except Exception as exc:  # Catch unexpected problems in detecting languages
        # TODO: Catch specific exceptions that can occur during tagging.
        logging.exception('- Tagging - ' + row[0] + '\n' + str(exc))
        driver.quit()
        return
    if lan_code == 'Empty':
        logging.warning('Tagging: Empty text - ')
        return
    if lan_code in ['Unknown', 'un', '']:
        logging.warning('Tagging: Unknown language - ')
        return
    if lan_code == 'Unreliable':
        logging.warning('Tagging: Low confidence - ')
        return

    row = [row[0]] + [lan_code] + row[1:]
    with Lock():
        with open('CRUX-McAfee-Cat_Lan.csv', 'a', newline='') as tagged:
            csv_writer = writer(tagged)
            csv_writer.writerow(row)


if __name__ == '__main__':
    nr_runners = 8
    with open('CRUX-McAfee-Cat.csv', 'r', newline='') as read_obj, \
            open('Tagging-errors.csv', 'w', newline='') as errors:
        inp_list = [x for x in list(reader(read_obj)) if x is not None]
        csv_error_writer = writer(errors)
        inp = random.sample(inp_list, 200)
        with Pool(nr_runners) as pool:
            pool.map(tag_row, inp)
