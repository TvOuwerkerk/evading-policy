const BaseCollector = require('./BaseCollector');

// eslint-disable-next-line no-unused-vars
class ScreenshotCollector extends BaseCollector {

    id() {
        return 'screenshots';
    }

    /**
     * Called after the crawl to retrieve the data. Can be async, can throw errors.
     *
     * @param {{finalUrl: string, urlFilter?: function(string):boolean}} options
     * @returns {Promise<Object>|Object}
     */
    getData(options) {
        //TODO: take screenshot and return
        return super.getData(options);
    }
}