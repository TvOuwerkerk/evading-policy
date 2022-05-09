# Evading the Policy

This is a release of the data and code of Thomas van Ouwerkerk's Master's Thesis titled "*Evading the Policy: a measurement on referrer policy circumvention in 3k e-commerce websites.*"

### Overview

The repository consists of four primary components.

- `Analysis/`: Contains the code used for processing and analysing the data gathered during crawling.
- `Listing/`: Contains the code and data used to create a corpus of ecommerce websites visited from the Netherlands.
- `ProductUrls/`: Contains the code used during the crawl to select links for further crawling. Uses a pretrained classifier written by Bogdan Covrig, published [here](https://github.com/BogDAAAMN/url-classifier-thesis).
- `tracker-radar-collector/`: Contains a fork of the [tracker-radar-collector](https://github.com/duckduckgo/tracker-radar-collector) project by DuckDuckGo. A ScreenshotCollector, integration of [Consent-O-Matic](https://github.com/cavi-au/Consent-O-Matic), and two `cli` options were added. Read more in its [README](./tracker-radar-collector/README.md)
  Note: after execution of our research (December 2021), a ScreenshotCollector and method of rejecting consent dialogs were independently added in the original project.
