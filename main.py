import os
import json
import datetime
import requests
import schedule
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()


class HermesProduct:
    def __init__(self, country, language, webhook):
        self.latest_skus = set()
        self.current_skus = set()
        self.country = country
        self.language = language
        self.webhook = webhook

        self.start_monitor()

    def get_product_content(self):
        try:
            response = requests.get(
                f"https://www.hermes.com/{self.country}/{self.language}/category/women/bags-and-small-leather-goods/bags-and-clutches/#|"
            )
            if response.status_code != 200:
                raise Exception("Failed to get response")

            soup = BeautifulSoup(response.text, "html.parser").find(
                class_="grid-container"
            )

            if not soup:
                raise Exception("Failed to get product content")

            return soup
        except Exception as e:
            print(e)

    def get_current_skus(self, product_content):
        product_items = product_content.find_all(class_="product-item")

        for product_item in product_items:
            sku = product_item.find("a")["href"].split("-")[-1][:-1]
            self.current_skus.add(sku)

    def get_product_data(self, product_content, sku):
        product_item = product_content.find("a", id=f"product-item-meta-link-{sku}")

        name = product_item.find(class_="product-item-name").text
        url = "https://hermes.com" + product_item["href"]
        price = product_item.find(class_="price").text
        image = "https:" + product_item.find("img")["src"]

        return {
            "name": name,
            "url": url,
            "country": self.country.upper(),
            "sku": sku,
            "price": price,
            "image": image,
        }

    def create_embed(self, data):
        return [
            {
                "color": 0x868E96,
                "title": data["name"],
                "url": data["url"],
                "thumbnail": {"url": data["image"]},
                "fields": [
                    {"name": "Country", "value": data["country"], "inline": "true"},
                    {"name": "SKU", "value": data["sku"], "inline": "true"},
                    {"name": "Price", "value": data["price"], "inline": "true"},
                ],
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            }
        ]

    def send_embed(self, embed):
        try:
            response = requests.post(
                self.webhook,
                data=json.dumps({"embeds": embed}),
                headers={"Content-Type": "application/json"},
            )
            if response.status_code != 204:
                raise Exception("Failed to send discord webhook")
        except Exception as e:
            print(e)

    def update_skus(self):
        self.latest_skus = self.current_skus
        self.current_skus.clear()

    def check_products(self):
        try:
            product_content = self.get_product_content()
            self.get_current_skus(product_content)

            new_skus = self.current_skus - self.latest_skus

            if not new_skus:
                self.update_skus()
                return

            for new_sku in new_skus:
                product_data = self.get_product_data(product_content, new_sku)
                embed = self.create_embed(product_data)
                self.send_embed(embed)

            self.update_skus()
        except Exception as e:
            print(e)

    def start_monitor(self):
        schedule.every(3).seconds.do(self.check_products)
        while True:
            schedule.run_pending()


HermesProduct("sg", "en", os.environ.get("DISCORD_WEBHOOK"))
