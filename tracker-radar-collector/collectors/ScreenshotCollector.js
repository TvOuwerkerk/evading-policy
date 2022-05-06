const BaseCollector = require('./BaseCollector');

class ScreenshotCollector extends BaseCollector {

    id() {
        return 'screenshots';
    }

    /**
     * @param {{cdpClient: import('puppeteer').CDPSession, url: string, type: import('./TargetCollector').TargetType}} targetInfo
     */
    addTarget({cdpClient, type}) {
        if (type === 'page') {
            this._cdpClient = cdpClient;
        }
    }

    /**
     * @returns {Promise<Screenshot>}
     */
    async getData() {
        const result = await this._cdpClient.send('Page.captureScreenshot');
        return result.data;
    }
}

module.exports = ScreenshotCollector;

/**
 * @typedef {string} Screenshot as Base64-encoded image data
 */