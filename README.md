# Data for term paper for vizualization, description and comparation of economic data

Simple python script for extracting second-hand flats data from sreality.<br>

Usage<br>
1. Create venv
2. Install requirements.txt
3. Activate venv
4. Run "scrapy runspider flats_data.py --logfile scrape.log -O results.json"<br>
This is possible, since the spider is located in the root folder

Alternatively, spider can be moved into the sreality//spiders folder, and stuff such as middlewares or proxies can be used<br>
(scrapy crawl flats_data --logfile scrape.log -O results.json)
