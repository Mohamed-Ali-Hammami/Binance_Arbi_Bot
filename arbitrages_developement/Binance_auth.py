import json
from requests.auth import AuthBase

class BinanceAuth(AuthBase):
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        print('initilized')

    def __call__(self, request):
        request.headers.update({
            'X-MBX-APIKEY': self.api_key,
        })
        return request


def read_config(file_path=r'arbitrages\config.json'):
    try:
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            api_key = data['API_KEYS']['API_KEY']
            secret_key = data['API_KEYS']['API_SECRET']
            return BinanceAuth(api_key, secret_key)
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        print(f"Error reading configuration: {e}")
        return None
# Test the BinanceAuth class
auth_instance = read_config()

if auth_instance is not None:
    print("BinanceAuth object created successfully.")
else:
    print("Failed to create BinanceAuth object.")
