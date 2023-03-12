import os

import requests, json, base64
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
text_to_speech_api_key_secret_path = os.environ.get('text_to_speech_api_key_secret_path')
res = client.access_secret_version(request={"name": text_to_speech_api_key_secret_path})

URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
API_KEY = res.payload.data.decode("UTF-8")


class TextToSpeech:
    
    def convert_text_to_speech(self, text):
        parameters = {"key": API_KEY}
        json_data = {
            "input": {"text": text},
            "voice": {"languageCode": "tr"},
            "audioConfig": {"audioEncoding": "MP3"}
        }
    
        response_bytes = requests.post(URL, params=parameters, json=json_data)
        response_string = response_bytes.content.decode('utf8')
        response = json.loads(response_string)
        
        encode_string = response['audioContent']
        decode_string = base64.b64decode(encode_string)
        return decode_string

