import os
import requests, json
import database_controller
from google.cloud import secretmanager
from time import time

client = secretmanager.SecretManagerServiceClient()
currency_api_key_secret_path = os.environ.get('currency_converter_api_key_secret_path')
res = client.access_secret_version(request={"name": currency_api_key_secret_path})

API_KEY = res.payload.data.decode("UTF-8")
URL = "https://api.apilayer.com/exchangerates_data/latest"


class CurrencyConverter:

    database_controller = None
    eur_keywords = {"eur", "euro", "euros", "yuro", "avro", "euroya", "euroa", "euronun", "eurocuk", "euro'a", "euro’a", "euro'nun", "euro’nun", "euro'ya", "euro’ya", "euroluk", "euro'luk", "euro’luk", "€"}
    usd_keywords = {"$", "usd", "dolar", "dollar", "dollars", "dolares", "dolara", "dolarlik", "dolarin", "dolarla", "dolar'a", "dolar'la", "dolar’a", "dolar’la", "dolar’in", "dolar'in", "dolarcik"}
    gbp_keywords = {"gbp", "pound", "pounds", "£", "pounda", "pound'a", "pound’a", "poundla", "pound'la", "pound’la", "poundin", "pound'in", "pound’in", "poundluk", "pound'luk", "pound’luk"}
    try_keywords = {"tl", "try", "lira"}
    all_keywords = {*eur_keywords, *usd_keywords, *gbp_keywords, *try_keywords}

    symbols = {"eur": '€', "usd": '$', "gbp": '£', "lira": '₺'}

    def check_for_currency_conversion(self, text):
        text = text.lower().split()
        for key in self.all_keywords:
            if key in text:
                return True

        return False

    def get_currency_conversion_as_text(self, text):
        last_update_time = self.database_controller.get_last_update_time_of_exchange_rates()
        if (time() - last_update_time) > 3600:
            self.update_exchange_rates()

        index, currency = self.find_currency(text)
        exchange_rate = self.database_controller.get_exchange_rate_for(currency)
        value = self.find_value(text, index)
        symbol = self.symbols["usd"] if currency == database_controller.rates_indexes.lira else "₺"
        if value:
            formatted_text = "{}{} = {}{}".format(round(value, 2), self.symbols[currency.name], round(value / exchange_rate, 2), symbol)
            return formatted_text

    def find_currency(self, text):
        text = text.lower().split()
        for word in text:
            if word in self.eur_keywords:
                index = text.index(word)
                return index, database_controller.rates_indexes.eur

        for word in text:
            if word in self.usd_keywords:
                index = text.index(word)
                return index, database_controller.rates_indexes.usd

        for word in text:
            if word in self.gbp_keywords:
                index = text.index(word)
                return index, database_controller.rates_indexes.gbp

        for word in text:
            if word in self.try_keywords:
                index = text.index(word)
                return index, database_controller.rates_indexes.lira

    def find_value(self, text, index):
        text = text.lower().split()
        if index != 0:
            try:
                value = float(text[index - 1].replace(',', '.'))
                return value
            except:
                pass

    def update_exchange_rates(self):
        headers = {
            "apikey": API_KEY
        }
        parameters = {
            "symbols": "EUR,USD,GBP",
            "base": "TRY"
        }

        response_bytes = requests.get(URL, headers=headers, params=parameters)
        response_string = response_bytes.content.decode('utf8')
        response = json.loads(response_string)

        self.database_controller.set_exchange_rates(response['rates'])
