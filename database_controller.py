import json
import os
from enum import Enum
from time import time

import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
firebase_admin_keys_secret_path = os.environ.get('firebase_admin_keys_secret_path')
response = client.access_secret_version(request={"name": firebase_admin_keys_secret_path})
firebase_admin_keys_json = json.loads(response.payload.data.decode("utf-8"))
cred = credentials.Certificate(firebase_admin_keys_json)

DATABASE_URL = os.environ.get("firebase_realtime_database_url")

firebase_admin.initialize_app(cred, {
    'databaseURL': DATABASE_URL
})

database_ref = db.reference()
rates_ref = database_ref.child("rates")
users_ref = database_ref.child("users")
groups_ref = database_ref.child("groups")
update_ids_ref = database_ref.child('updates')


class DatabaseController:

    def add_group_member(self, chat_id, user_id, username):
        groups_ref.update({
            f'{chat_id}/{user_id}': {
                'username': username,
                'echo': True
            }
        })

    def get_group_members(self, chat_id):
        return groups_ref.child(str(chat_id)).get()

    def remove_user_data(self, chat_id, user_id):
        groups_ref.update({
            f'{chat_id}/{user_id}/echo': False
        })

    def get_last_update_time_of_exchange_rates(self):
        rates = rates_ref.get()
        return rates['timestamp'] if rates else 0

    def set_exchange_rates(self, rates):
        rates_ref.set({
            'eur': rates['EUR'],
            'usd': rates['USD'],
            'gbp': rates['GBP'],
            'lira': (1 / rates['USD']),
            'timestamp': time()
        })

    def get_exchange_rate_for(self, currency):
        rates = rates_ref.get()
        return rates[currency.name]

    def get_latest_update_id(self):
        update_ids = update_ids_ref.get()
        return update_ids['handled_updates']['last']

    def save_last_handled_update_id(self, update_id):
        update_ids_ref.update({
            'handled_updates/last': update_id
        })


class rates_indexes(Enum):
    eur = 0
    usd = 1
    gbp = 2
    lira = 3
