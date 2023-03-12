import requests, json, os
import urllib3

import database_controller
import currency_converter
import text_to_speech
import reddit
from google.cloud import secretmanager


class TelegramGroupHelper:
    client = secretmanager.SecretManagerServiceClient()
    bot_token_secret_path = os.environ.get('bot_token_secret_path')
    response = client.access_secret_version(request={"name": bot_token_secret_path})
    bot_token = response.payload.data.decode("UTF-8")

    URL = "https://api.telegram.org/bot{}/".format(bot_token)

    database_controller = database_controller.DatabaseController()
    currency_converter = currency_converter.CurrencyConverter()
    text_to_speech = text_to_speech.TextToSpeech()
    reddit = reddit.Reddit()

    currency_converter.database_controller = database_controller

    def send_message(self, chat_id, text, reply_to=None):
        json_data = {
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": reply_to
        }
        send_url = self.URL + 'sendMessage'
        requests.post(send_url, json=json_data)

    def send_voice(self, chat_id, voice_bytes, reply_to=None, caption=None):
        json_data = {
            "chat_id": chat_id,
            "caption": "from: @" + caption
        }
        files = {"voice": voice_bytes}
        send_url = self.URL + 'sendVoice'
        response_bytes = requests.post(send_url, params=json_data, files=files)
        response_string = response_bytes.content.decode('utf8')
        json.loads(response_string)

    def send_image(self, chat_id, image_url, caption=''):
        json_data = {
            "chat_id": chat_id,
            "photo": image_url,
            "caption": caption,
        }
        send_url = self.URL + 'sendPhoto'
        response = urllib3.PoolManager().request('POST', send_url, fields=json_data)
        return response.status

    def send_video(self, chat_id, video_url, caption='', reply_to=None):
        json_data = {
            "chat_id": chat_id,
            "video": video_url,
            "caption": caption,
            "reply_to_message_id": reply_to
        }
        send_url = self.URL + 'sendVideo'
        requests.post(send_url, params=json_data)

    def send_video_with_files(self, chat_id, files, caption='', width: int = None, height: int = None, duration: int = None, thumbnail = None, reply_to=None):
        json_data = {
            'chat_id': chat_id,
            'caption': caption,
            'width': width,
            'height': height,
            'duration': duration,
            'thumb': thumbnail,
            "reply_to_message_id": reply_to
        }
        files = {
            'video': files
        }
        send_url = self.URL + 'sendVideo'
        response = requests.post(send_url, params=json_data, files=files)
        print(response.json())

    def delete_message(self, message):
        json_data = {
            "chat_id": message['chat']['id'],
            "message_id": message['message_id'],
        }
        send_url = self.URL + 'deleteMessage'
        requests.post(send_url, json=json_data)

    def add_group_member(self, message):
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        username = message['from']['username']
        self.database_controller.add_group_member(chat_id, int(user_id), username)
        self.delete_message(message)

    def remove_group_member(self, message):
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        self.database_controller.remove_user_data(chat_id, int(user_id))
        self.delete_message(message)

    def convert_text_to_speech(self, message):
        text = message['text'].lstrip("/tts").strip()
        if len(text.split()) != 0:
            voice_bytes = self.text_to_speech.convert_text_to_speech(text)
            self.send_voice(message['chat']['id'], voice_bytes, message['message_id'], message['from']['username'])
            self.delete_message(message)

    def handle_reddit_url(self, message, url: str):
        print('handling reddit url')
        json_data = self.reddit.get_json_data(url)

        if json_data is None:
            print('could not get valid json_data')
            return

        if not self.reddit.has_media(json_data):
            print('reddit link has no media')
            return

        domain = self.reddit.get_domain(json_data)

        if domain == reddit.Domains.Reddit:
            print('domain is reddit')
            self.handle_reddit_media_domain(message, json_data)

        elif domain == reddit.Domains.Imgur:
            print('domain is imgur')
            self.handle_imgur_media_domain(message, json_data)

    def handle_reddit_media_domain(self, message, json_data):
        media_type = self.reddit.get_reddit_media_type(json_data)
        caption = self.reddit.get_caption(json_data)
        chat_id = message['chat']['id']
        url = json_data['url']
        status = 200

        if media_type == reddit.RedditMediaTypes.Video:
            if self.reddit.requires_ffmpeg(json_data):
                print('requires ffmpeg')
                video_files = self.reddit.get_files(json_data)
                width, height, duration = self.reddit.get_reddit_domain_video_dimensions(json_data)
                self.send_video_with_files(chat_id, video_files, caption=caption, width=width, height=height,
                                           duration=duration, thumbnail=json_data['thumbnail'])
            else:
                print('not requires ffmpeg')
                self.send_video(chat_id, url, caption)

        else:
            print('assuming it is reddit image')
            status = self.send_image(chat_id, url, caption)

        if status == 200:
            self.delete_message(message)

    def handle_imgur_media_domain(self, message, json_data):
        chat_id = message['chat']['id']
        caption = self.reddit.get_caption(json_data)
        imgur_media_type, imgur_json = self.reddit.get_imgur_media_type_and_response(json_data)

        if imgur_media_type == reddit.ImgurMediaTypes.Image:
            self.send_image(chat_id, imgur_json['link'], caption)
        elif imgur_media_type == reddit.ImgurMediaTypes.Video:
            self.send_video(chat_id, imgur_json['mp4'], caption)

        self.delete_message(message)

    def message_handler(self, message):
        if 'entities' in message.keys():
            for entity in message['entities']:
                if entity['type'] == 'bot_command':
                    command = message['text'][entity['offset']:entity['offset'] + entity['length']]

                    if command == '/all':
                        self.echo_message(message)
                    elif command == '/add':
                        self.add_group_member(message)
                    elif command == '/remove':
                        self.remove_group_member(message)
                    elif command == '/tts':
                        self.convert_text_to_speech(message)

                elif entity['type'] == 'url':
                    url = message['text'][entity['offset']:entity['offset'] + entity['length']]

                    if self.reddit.is_valid_url(url):
                        self.handle_reddit_url(message, url)

        if "text" in message.keys():
            if self.currency_converter.check_for_currency_conversion(message['text']):
                text = self.currency_converter.get_currency_conversion_as_text(message['text'])
                if text:
                    self.send_message(message['chat']['id'], text, message['message_id'])

    def echo_message(self, message):
        chat_id = message['chat']['id']
        chat = self.database_controller.get_group_members(chat_id)
        text = message['text'].lstrip("/all") + "\n"
        if chat is not None:
            for member_id in chat:
                text += "\n@" + str(chat[member_id]['username'])
                if message['from']['username'] == chat[member_id]['username']:
                    text += ' 🐣'
        self.send_message(chat_id, text)
        self.delete_message(message)

    def update_handler(self, update):
        if 'update_id' in update.keys():
            if update['update_id'] <= self.database_controller.get_latest_update_id():
                return

        self.database_controller.save_last_handled_update_id(update['update_id'])

        if 'message' in update.keys():
            self.message_handler(update['message'])
