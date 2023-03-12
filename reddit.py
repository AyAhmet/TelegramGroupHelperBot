import urllib3, json, os, subprocess
from enum import Enum
from subprocess import PIPE
from google.cloud import secretmanager

reddit_domains = {'i.redd.it', 'v.redd.it'}
imgur_domains = {'i.imgur.com', 'imgur.com'}
all_domains = {*reddit_domains, *imgur_domains}


class Reddit:
    client = secretmanager.SecretManagerServiceClient()
    imgur_secret_path = os.environ.get('imgur_secret_path')
    response = client.access_secret_version(request={"name": imgur_secret_path})
    imgur_client_id = response.payload.data.decode("UTF-8")

    def is_valid_url(self, url: str):
        return url.startswith("https://www.reddit.com/r")

    def get_json_data(self, url: str):
        url = url.split('?')[0] + '.json'
        response = urllib3.PoolManager().request('GET', url, headers={'User-agent': 'My Telegram Group Helper Bot v0.001'})
        json_raw = json.loads(response.data)

        if type(json_raw) is list and 'data' in json_raw[0].keys():
            json_data = json_raw[0]['data']['children'][0]['data']
            while 'crosspost_parent_list' in json_data.keys():
                json_data = json_data['crosspost_parent_list'][0]
            return json_data

        return None

    def has_media(self, json_data):
        if 'domain' not in json_data.keys():
            return False

        return json_data['domain'] in all_domains

    def get_url(self, json_data):
        return json_data['url']

    def get_domain(self, json_data):
        if json_data['domain'] in reddit_domains:
            return Domains.Reddit
        elif json_data['domain'] in imgur_domains:
            return Domains.Imgur

    def get_reddit_media_type(self, json_data):
        if json_data['is_video'] or json_data['url'].endswith('.gif'):
            return RedditMediaTypes.Video
        else:
            return RedditMediaTypes.Image

    def get_imgur_media_type_and_response(self, json_data):
        imgur_id = json_data['url'].split('/')[-1].split('.')[0]
        imgur_response = urllib3.PoolManager().request('GET', f'https://api.imgur.com/3/image/{imgur_id}', headers={'Authorization': f'Client-ID {self.imgur_client_id}'})

        if imgur_response.status != 200:
            imgur_response = urllib3.PoolManager().request('GET', f'https://api.imgur.com/3/gallery/{imgur_id}', headers={'Authorization': f'Client-ID {self.imgur_client_id}'})
        if imgur_response.status != 200:
            return None, None

        imgur_json = json.loads(imgur_response.data)
        imgur_json = imgur_json['data']

        if imgur_json['in_gallery']:
            return ImgurMediaTypes.Gallery, imgur_json
        elif imgur_json['type'].startswith('image'):
            return ImgurMediaTypes.Image, imgur_json
        elif imgur_json['type'].startswith('video'):
            return ImgurMediaTypes.Video, imgur_json

    def get_caption(self, json_data):
        return 'r/' + json_data['subreddit'] + ' - ' + json_data['title'] + '\n\nreddit.com' + json_data['permalink']

    def requires_ffmpeg(self, json_data):
        return json_data['is_video']

    def get_reddit_domain_video_dimensions(self, json_data):
        video = json_data['media']['reddit_video']
        return video['width'], video['height'], video['duration']

    def get_files(self, json_data):
        video_url = json_data['media']['reddit_video']['fallback_url']
        audio_url = video_url.split('DASH_')[0] + 'DASH_audio.mp4'
        process = subprocess.Popen(
            ['ffmpeg', "-i", video_url, "-i", audio_url, "-f", "ismv", "-fs", "50M", "-c:v", "copy", "-c:a", "copy",
             "-preset", "ultrafast", "-"], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        output, error = process.communicate()
        process.kill()
        return output

    def get_video_url(self, json_data):
        if json_data['is_reddit_media_domain']:
            return json_data['media']['reddit_video']['fallback_url']
        else:
            return json_data['preview']['reddit_video']['fallback_url']


class RedditMediaTypes(Enum):
    Image = 0,
    Video = 1


class ImgurMediaTypes(Enum):
    Image = 0,
    Video = 1,
    Gallery = 2


class Domains(Enum):
    Reddit = 0,
    Imgur = 1,
