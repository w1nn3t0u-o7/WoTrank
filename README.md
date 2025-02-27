# WoT Tournaments Player Ranking

This project is designed to parse information about player performance in World of Tanks tournaments from replays posted on websites. It collects data and creates a database and ranking system.
## Project Overview

This project uses a Python script to scrape data from multiple World of Tanks replay URLs. The collected data is processed with pandas to create a comprehensive dataset of player performance, which can be exported to various formats.
Features

- Fetches and parses data from World of Tanks replay URLs.
- Extracts valuable battle information such as battle duration, map name, and player statistics.
- Processes and normalizes the data for further analysis.
- Combines data from multiple replays into a single dataset.
- Removes duplicate entries and cleans the data.
- Provides options to export the data to Excel or JSON formats.

## Installation

Clone the repository:
```sh
git clone https://github.com/w1nn3t0u-o7/WoT-tournaments-player-ranking.git
cd WoT-tournaments-player-ranking
```

## Usage

- Update the urls list in web_scraping.py with the URLs of the replays you want to scrape.
- Run the script:
```sh
python web_scraping.py
```
- The script will output the processed data.
