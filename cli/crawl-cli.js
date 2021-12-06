const path = require('path');
const fs = require('fs');
const chalk = require('chalk').default;
const runCrawlers = require('../crawlerConductor');
const program = require('commander');
const ProgressBar = require('progress');
const URL = require('url').URL;
const crypto = require('crypto');
const {getCollectorIds, createCollector} = require('../helpers/collectorsList');
const {metadataFileExists, createMetadataFile} = require('./metadataFile');
// eslint-disable-next-line no-unused-vars
const BaseCollector = require('../collectors/BaseCollector');
const ScreenshotCollector = require('../collectors/ScreenshotCollector');
const tld = require('tld-extract');

program
    .option('-o, --output <path>', '(required) output folder')
    .option('-u, --url <url>', 'single URL')
    .option('-i, --input-list <path>', 'path to list of URLs')
    .option('-d, --data-collectors <list>', `comma separated list of data collectors: ${getCollectorIds().join(', ')} (all by default)`)
    .option('-l, --log-file <path>', 'save log data to a file')
    .option('-v, --verbose', 'print log data to the screen')
    .option('-c, --crawlers <number>', 'overwrite the default number of concurent crawlers')
    .option('-f, --force-overwrite', 'overwrite existing output files')
    .option('-3, --only-3p', 'don\'t save any first-party data')
    .option('-m, --mobile', 'emulate a mobile device')
    .option('-p, --proxy-config <host>', 'use an optional proxy configuration')
    .option('-r, --region-code <region>', 'optional 2 letter region code. Used for metadata only.')
    .option('-a, --disable-anti-bot', 'disable anti bot detection protections injected to every frame')
    .option('--chromium-version <version_number>', 'use custom version of chromium')
    .option('-s, --scrape-links', 'collect and save links found on visited pages')
    .option('-j, --input-json <path>', 'path to admin json file')
    .parse(process.argv);

/**
 * @param {string[]} inputUrls
 * @param {string} outputDir
 * @param {boolean} verbose
 * @param {string} logPath
 * @param {number} numberOfCrawlers
 * @param {BaseCollector[]} dataCollectors
 * @param {boolean} forceOverwrite
 * @param {boolean} filterOutFirstParty
 * @param {boolean} emulateMobile
 * @param {string} proxyHost
 * @param {string} regionCode
 * @param {boolean} antiBotDetection
 * @param {string} chromiumVersion
 * @param {boolean} scrapeLinks
 */
async function run(inputUrls, outputDir, verbose, logPath, numberOfCrawlers, dataCollectors, forceOverwrite, filterOutFirstParty, emulateMobile, proxyHost, regionCode, antiBotDetection, chromiumVersion,scrapeLinks) {
    const logFile = logPath ? fs.createWriteStream(logPath, {flags: 'w'}) : null;

    /**
     * @type {function(...any):void}
     */
    const log = (...msg) => {
        if (verbose) {
            // eslint-disable-next-line no-console
            console.log(...msg);
        }

        if (logFile) {
            logFile.write(msg.join(' ') + '\n');
        }
    };

    /**
     * For a given URL, create the base for the file names where its data should be stored.
     * Note that a file extension needs to be added after getting the return value of this method.
     * @type {function(...any):string}
     * @param {URL} url
     */
    const createOutputFileName = (url => {
        let hash = crypto.createHash('sha1').update(url.toString()).digest('hex');
        hash = hash.substring(0, 4); // truncate to length 4
        return `${url.hostname}_${hash}`;
    });

    /**
     * For a given URL, return the full path to the directory where its data should be stored
     * @type {function(...any):string}
     * @param {URL} url
     */
    const createOutputPath = (url => (program.inputJson ? path.join(outputDir,`data.${tld(url).domain}`) : outputDir));

    //Filter out invalid URLS and ones for which an output file already exists (if forceOverwrite is false)
    const urls = inputUrls.filter(urlString => {
        /**
         * @type {URL}
         */
        let url;

        try {
            url = new URL(urlString);
        } catch(e) {
            log(chalk.yellow('Invalid URL:'), urlString);
            return false;
        }

        if (forceOverwrite !== true) {
            // filter out entries for which result file already exists
            const outputFile = path.join(createOutputPath(url),`${createOutputFileName(url)}.json`);
            if (fs.existsSync(outputFile)) {
                log(chalk.yellow(`Skipping "${urlString}" because output file already exists.`));
                return false;
            }
        }

        return true;
    });

    // Truncate a given string. Useful for printing long urls in progressbar
    const truncateURL = (url = '') => {
        const TRUNCATE_LENGTH = 57;
        if (url.length > TRUNCATE_LENGTH) {
            return `${url.substring(0,TRUNCATE_LENGTH)}...`;
        }
        return url;
    };

    // show progress bar only if we are not printing all logs to screen (verbose)
    const progressBar = (verbose || urls.length === 0) ? null : new ProgressBar('[:bar] :percent ETA :etas fail :fail% :site', {
        complete: chalk.green('='),
        incomplete: ' ',
        total: urls.length,
        width: 30
    });

    let failures = 0;
    let successes = 0;
    const updateProgress = (site = '') => {
        if(progressBar) {
            progressBar.tick({
                site,
                fail: (failures / (failures + successes) * 100).toFixed(1)
            });
        }
    };

    /**
     * For a given URL and path to output directory of this URL, add the url to 'visited'
     * @param {URL} url
     * @param {string} outputPath
     */
    const tagURLVisited = (url, outputPath = '',) => {
        const urlDomain = tld(url).domain;
        const adminPath = path.join(`${outputPath}`,`admin.${urlDomain}.json`);
        let adminData = JSON.parse(fs.readFileSync(adminPath).toString());
        adminData.visited.push(url);
        fs.writeFileSync(adminPath, JSON.stringify(adminData, null, 2));
    };


    /**
     * @param {URL} url
     * @param {import('../crawler').CollectResult} data
     */
    const dataCallback = (url, data) => {
        successes++;
        updateProgress(truncateURL(url.toString()));
        const outputPath = createOutputPath(url); //Path to directory where output will be stored for this url
        const outputFileName = createOutputFileName(url); //Base name for files where data is stored for this url
        const outputFileImg = path.join(outputPath,`${outputFileName}.png`); //Full path to file where img data is stored for this url
        const outputFileLinks = path.join(outputPath,`links.${outputFileName}.json`); //Full path to file where links data is stored for this url

        let screenshotID = new ScreenshotCollector().id();
        if (screenshotID in data.data) {
            let decodedImg = Buffer.from(data.data[screenshotID],'base64');
            fs.writeFileSync(outputFileImg, decodedImg);
            data.data[screenshotID] = `Screenshot saved to ${outputFileImg}`;
        }

        if(scrapeLinks) {
            const links = data.data.links;
            data.data.links = `Internal links were collected and saved to ${outputFileLinks}`;
            fs.writeFileSync(outputFileLinks,JSON.stringify(links, null, 2));

        } else{
            data.data.links = 'No internal links were collected';
        }

        if(program.inputJson) {
            //Remove crawled url from 'tocrawl' in admin file. Add to 'visited'.
            tagURLVisited(url, outputPath);
        }

        //Write crawled data to outputfile for this url
        fs.writeFileSync(path.join(outputPath,`${outputFileName}.json`), JSON.stringify(data, null, 2));
    };

    /**
     * @param {string} url
     */
    const failureCallback = url => {
        failures++;
        updateProgress(truncateURL(url));
        tagURLVisited(new URL(url), createOutputPath(url));
    };

    const startTime = new Date();

    log(chalk.cyan(`Start time: ${startTime.toUTCString()}`));
    log(chalk.cyan(`Number of urls to crawl: ${urls.length}`));

    if (progressBar) {
        progressBar.render();
    }

    let fatalError = null;

    try {
        await runCrawlers({
            urls,
            logFunction: log,
            dataCollectors,
            numberOfCrawlers,
            failureCallback,
            dataCallback,
            filterOutFirstParty,
            emulateMobile,
            proxyHost,
            antiBotDetection,
            chromiumVersion,
            scrapeLinks
        });
        log(chalk.green('\n✅ Finished successfully.'));
    } catch(e) {
        log(chalk.red('\n🚨 Fatal error.'), e);
        fatalError = e;
    }

    const endTime = new Date();

    log(chalk.cyan(`Finish time: ${endTime.toUTCString()}`));
    log(chalk.cyan(`Sucessful crawls: ${successes}/${urls.length} (${(successes / urls.length * 100).toFixed(2)}%)`));
    log(chalk.cyan(`Failed crawls: ${failures}/${urls.length} (${(failures / urls.length * 100).toFixed(2)}%)`));

    createMetadataFile(outputDir, {
        startTime,
        endTime,
        fatalError,
        numberOfCrawlers,
        filterOutFirstParty,
        emulateMobile,
        proxyHost,
        regionCode,
        scrapeLinks,
        dataCollectors: dataCollectors.map(c => c.id()),
        successes,
        failures,
        urls: inputUrls.length,
        skipped: inputUrls.length - urls.length
    });
}

const verbose = Boolean(program.verbose);
const forceOverwrite = Boolean(program.forceOverwrite);
const filterOutFirstParty = Boolean(program.only3p);
const emulateMobile = Boolean(program.mobile);
const scrapeLinks = Boolean(program.scrapeLinks);
/**
 * @type {BaseCollector[]}
 */
let dataCollectors = null;
/**
 * @type {string[]}
 */
let urls = null;

const crawlDir = `${program.inputJson}-crawl`;
if (!fs.existsSync(crawlDir)) {
    fs.mkdirSync(crawlDir);
}

if (typeof program.dataCollectors === 'string') {
    const dataCollectorsIds = program.dataCollectors.split(',').map(n => n.trim()).filter(n => n.length > 0);

    dataCollectors = [];

    dataCollectorsIds.forEach(id => {
        if (!getCollectorIds().includes(id)) {
            // eslint-disable-next-line no-console
            console.log(chalk.red(`Unknown collector "${id}".`), `Valid collector names are: ${getCollectorIds().join(', ')}.`);
            process.exit(1);
        }

        dataCollectors.push(createCollector(id));
    });
} else {
    dataCollectors = getCollectorIds().map(id => createCollector(id));
}

if (program.url) {
    urls = [program.url];
} else if(program.inputList) {
    urls = fs.readFileSync(program.inputList).toString().split('\n').map(u => u.trim());
} else if(program.inputJson) {
    urls = [];
    // Read list of domains that need to be crawled
    //TODO: trim input string before splitting?
    let data = Array.from(fs.readFileSync(program.inputJson).toString().trim().split('\n').map(u => u.trim()));
    data.forEach(domain => {
        let strippedDomain = '';
        try {
            strippedDomain = tld(domain).domain;
        } catch (e) {
            console.log('Data: ', data);
            console.log('Type: ', typeof data);
            console.log('Item: ', domain);
            console.log('Type: ', typeof domain);
        }

        // For each domain that needs to be crawled, make a path for the associated admin json file
        const dataPath = path.join(`${crawlDir}`,`data.${strippedDomain}`);
        const adminPath = path.join(dataPath,`admin.${strippedDomain}.json`);
        let adminData = '';

        // If the admin file exists, get the 'tocrawl' list of urls that need to be visited. Else create one
        if (fs.existsSync(adminPath)) {
            adminData = fs.readFileSync(adminPath).toString();
        } else {
            adminData = `{"tocrawl":["${domain}"], "visited":{}, "product":{}}`;
            fs.mkdir(dataPath, {recursive: true}, err => {
                if(err) {
                    console.log(`Error creating data.dir: ${err.message}`);
                }
            });
            fs.writeFileSync(adminPath, JSON.stringify(adminData));
        }
        let adminDataDict = JSON.parse(adminData);
        // Add 'tocrawl' list of urls from admin file to the list of urls that get sent to the crawlerConductor
        urls.push(...adminDataDict.tocrawl);

        // Empty out admin file's 'tocrawl' list. Crawled URLs will be added to 'visited' list later
        adminDataDict.tocrawl = [];
        fs.writeFileSync(adminPath, JSON.stringify(adminDataDict));
    });
}

// If admin.json input, saving files needs to be strictly structured, thus ignore program.output in that case
if (!urls || (!program.output && !program.inputJson)) {
    program.help();
} else {
    urls = urls.map(url => {
        if (url.startsWith('http://') || url.startsWith('https://')) {
            return url;
        }
        return `http://${url}`;
    });

    const outputFile = program.inputJson ? crawlDir : program.output;
    const logFile = program.inputJson ? path.join(crawlDir,`${program.inputJson.split(path.sep).slice(-1)[0]}.log`) : program.logFile;

    if (fs.existsSync(outputFile)) {
        if (metadataFileExists(outputFile) && !forceOverwrite) {
            // eslint-disable-next-line no-console
            console.log(chalk.red('Output folder already exists and contains metadata file.'), 'Use -f to overwrite.');
            process.exit(1);
        }
    } else {
        fs.mkdirSync(program.output);
    }

    run(urls, outputFile, verbose, logFile, program.crawlers || null, dataCollectors, forceOverwrite, filterOutFirstParty, emulateMobile, program.proxyConfig, program.regionCode, !program.disableAntiBot, program.chromiumVersion, scrapeLinks);
}
