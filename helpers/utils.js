// eslint-disable-next-line no-unused-vars
const puppeteer = require('puppeteer');

const MAX_WAIT_TIME_FOR_CMP_DETECTION = 6000;
const SLEEP_TIME_FOR_CMP_DETECTION = 300;
const POST_CMP_DETECTION_WAIT_TIME = 2500;

/**
 * @param {number} time
 */
function sleep(time) {
    return new Promise(resolve => setTimeout(resolve, time));
}

//First, make ready eventListener: foundCMPEvent
//Create new ConsentEngine object that will trigger foundCMPEvent event.
/**
 * @param {puppeteer.Page} page
 * @param {(arg0: string) => void} log
 * @param {string} cmpAction //Values can be 'NO_ACTION', 'ACCEPT_ALL', 'REJECT_ALL'
 */
async function findCMP(page, log=null, cmpAction = 'NO_ACTION') {
    let cmpDetected =false;
    await page.exposeFunction('foundCMPEvent', cmpName => {
        log(`CMP detected on ${page.url()}: ${cmpName}`);
        cmpDetected = true;
    });
    await page.evaluate(cmpAction => {
        let config = cmpConfigData;
        let consentTypes = GDPRConfig.defaultValues;
        let debugValues = GDPRConfig.defaultDebugFlags;
        if(cmpAction === 'NO_ACTION') {
            debugValues.skipActions = true;
        } else if(cmpAction === 'ACCEPT_ALL') {
            consentTypes = {
                A: true,
                B: true,
                D: true,
                E: true,
                F: true,
                X: true
            };
        }
        console.log("Action: ", cmpAction);
        let engine = new ConsentEngine(config, consentTypes, debugValues, async stats => {
            await window.foundCMPEvent(JSON.stringify(stats));
        });
    }, cmpAction);
    //Sleep until CMP can be detected!
    //MAX_WAIT_TIME_FOR_CMP_DETECTION was calculated based on 1K crawl
    let waitTimeSum = 0;
    while(!cmpDetected && waitTimeSum < MAX_WAIT_TIME_FOR_CMP_DETECTION) {
        //log('Not detected CMP yet!');
        waitTimeSum += SLEEP_TIME_FOR_CMP_DETECTION;
        await sleep(SLEEP_TIME_FOR_CMP_DETECTION);
    }
    if(cmpDetected) {
        log(`Will wait ${POST_CMP_DETECTION_WAIT_TIME}ms after CMP detected!`);
        await page.waitForTimeout(POST_CMP_DETECTION_WAIT_TIME);
    }
}

module.exports = {
    findCMP,
    sleep
};