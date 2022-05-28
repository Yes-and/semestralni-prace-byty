import json
import re

import scrapy


class FlatsDataSpider(scrapy.Spider):
    name = "flats_data"

    custom_settings = {
        "DOWNLOAD_DELAY": 0.1,
    }

    regions = {
        1: "Jihočeský kraj",
        2: "Plzeňský kraj",
        3: "Karlovarský kraj",
        4: "Ústecký kraj",
        5: "Liberecký kraj",
        6: "Královéhradecký kraj",
        7: "Pardubický kraj",
        8: "Olomoucký kraj",
        9: "Zlínský kraj",
        10: "Praha",
        11: "Středočeský kraj",
        12: "Moravskoslezský kraj",
        13: "Vysočina",
        14: "Jihomoravský kraj",
    }

    price_types = {
        "Celková cena": "total",
        "za m²": "per_m2",
    }

    unit_types = {
        1: "Byt",
    }

    def start_requests(self):

        results_per_page = 999

        for region_number in self.regions.keys():
            item = dict()

            url = (
                "https://www.sreality.cz/api/cs/v2/estates?"
                "building_condition=1%7C2%7C3%7C8%7C9&"
                "category_main_cb=1&"
                "category_sub_cb="
                "2%7C3%7C4%7C5%7C6%7C7%7C8%7C9%7C10%7C11%7C12&"
                "category_type_cb=1&"
                f"locality_region_id={region_number}&"
                "no_auction=1&"
                f"per_page={results_per_page}&"
                "page=1"
            )
            item["region"] = self.regions[region_number]

            yield scrapy.FormRequest(
                url=url,
                method="GET",
                callback=self.parse,
                meta={"item": item},
            )

    def parse(self, response):

        data = json.loads(response.text)
        properties = data["_embedded"]["estates"]

        for entry in properties:
            item = response.meta["item"].copy()

            price = entry["price_czk"].get("value_raw", [])
            if price:
                item["Cena"] = int(price)

            price_type = entry["price_czk"].get("name", [])
            if price_type:
                item["Typ_ceny"] = self.price_types[price_type]

            api_detail = entry["_links"]["self"]["href"]
            item["api_detail"] = f"https://www.sreality.cz/api{api_detail}"

            yield scrapy.FormRequest(
                url=item["api_detail"],
                method="GET",
                callback=self.scrape_detail,
                meta={"item": item},
            )

        result_size = data.get("result_size", [])
        if result_size:
            per_page = data.get("per_page", [])
            page = data.get("page", [])
            if per_page and page:
                if int(page) * int(per_page) < int(result_size):
                    yield scrapy.FormRequest(
                        url=response.request.url.replace(
                            f"&page={int(page)}", f"&page={int(page)+1}"
                        ),
                        method="GET",
                        callback=self.parse,
                        meta={"item": response.meta["item"].copy()},
                    )

    def scrape_detail(self, response):
        item = response.meta["item"].copy()

        data = json.loads(response.text)

        disposition = re.findall(
            r"(\d{1}\s?\+\s?(?:kk|\d{1}))", data["name"]["value"]
        )
        if disposition:
            item["Dispozice"] = disposition[0].replace(" ", "")

        for entry in data["items"]:
            name = entry["name"]
            value = entry["value"]

            acceptable_columns = [
                "Stavba",
                "Stav objektu",
                "Vlastnictví",
                "Výtah",
            ]

            unparsed_columns = [
                "Podlaží",
                "Užitná plocha",
                "Obytná plocha",
                "Celková plocha",
                "Plocha podlahová",
                "Energetická náročnost budovy",
                "Balkón",
                "Lodžie",
                "Terasa",
            ]

            if name in acceptable_columns:
                item[name] = value
            elif name in unparsed_columns:
                if name in "Podlaží":
                    floor = re.findall(r"\d{1,}", value)
                    if floor:
                        item[name] = int(floor[0])
                elif "plocha" in name.lower():
                    area = re.findall(r"\d+(?:[,\.]\d+)?", value)
                    if area:
                        item[name] = float(area[0].replace(",", "."))
                elif name in [
                    "Balkón",
                    "Lodžie",
                    "Terasa",
                ]:
                    if type(value) == bool:
                        item[name] = value
                    elif type(value) == str:
                        area = re.findall(r"\d+(?:[,\.]\d+)?", value)
                        if area:
                            item[name] = float(area[0].replace(",", "."))
                    elif type(value) == int or type(value) == float:
                        item[name] = float(value)
                elif "Energetická náročnost budovy" in name:
                    energy_class = re.findall(r"Třída ([A-G]{1})", value)
                    if energy_class:
                        item[name] = energy_class[0]

            unit_type = data["seo"]["category_main_cb"]
            item["typ"] = self.unit_types[unit_type]

        yield item
