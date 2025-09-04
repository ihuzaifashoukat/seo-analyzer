from datetime import datetime
import requests

def make_request(url, headers: dict, timeout: int, method: str = "get", **kwargs):
    try:
        kwargs.setdefault('stream', True)
        start_time = datetime.now()
        response = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
        end_time = datetime.now()
        ttfb = (end_time - start_time).total_seconds()
        return response, ttfb
    except requests.exceptions.RequestException as e:
        print(f"Request failed for {url} in TechnicalSEO: {e}")
        return None, None

def get_asset_response(asset_url: str, headers: dict, timeout: int):
    try:
        return requests.get(asset_url, headers=headers, timeout=timeout, allow_redirects=True)
    except requests.exceptions.RequestException:
        return None

