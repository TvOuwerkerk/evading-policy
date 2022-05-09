# Evading the Policy

This is a release of the data and code of Thomas van Ouwerkerk's Master's Thesis titled "*Evading the Policy: a measurement on referrer policy circumvention in 3k e-commerce websites.*"

### Overview

The repository consists of four primary components.

- `Analysis/`: Contains the code used for processing and analysing the data gathered during crawling.
- `Listing/`: Contains the code and data used to create a corpus of ecommerce websites visited from the Netherlands.
- `ProductUrls/`: Contains the code used during the crawl to select links for further crawling. Uses a pretrained classifier written by Bogdan Covrig, published [here](https://github.com/BogDAAAMN/url-classifier-thesis).
- `tracker-radar-collector/`: Contains a fork of the [tracker-radar-collector](https://github.com/duckduckgo/tracker-radar-collector) project by DuckDuckGo. A ScreenshotCollector, integration of [Consent-O-Matic](https://github.com/cavi-au/Consent-O-Matic), and two `cli` options were added. Read more in its [README](./tracker-radar-collector/README.md)
  Note: after execution of our research (December 2021), a ScreenshotCollector and method of rejecting consent dialogs were independently added in the original project.

### Analysis

This directory contains:

- Python script for processing crawled data (`postProcessing.py`)
- Python script for analysing said data (`analysis.py`)
- Notebook for visualising analysed data and plots generated by executing all cells in this notebook (`analysisVisualisation.ipynb, /plots/`)
-  Files containing processed data (`results.csv, policy_results.json`)

### Listing

This directory contains scripts for:

- processing the URLs gained from the Chrome User Experience Report (CrUX)
- normalising URLs, matching them to a Tranco list to order them by ranking
- tagging URLs with specific McAfee TrustedSource categories
- running a crawl to determine which languages websites are written in

### ProductUrls

This directory contains a script and pretrained model for determining whether a URL belongs to a product page and assigning a probability. This script was used in conjunction with the `-j` and `-s` command line options in Tracer Radar Collector to run iterative crawls, discovering new links to crawl in each iteration.

### tracker-radar-collector

This directory contains a fork of the Tracker Radar Collector project. This was used to crawl over 3k ecommerce websites to gather data on use and circumvention of the `referrer policy` HTTP header. Read more on the changes made and its use [here](./tracker-radar-collector/README.md)

