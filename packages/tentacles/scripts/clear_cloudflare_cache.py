import os
import sys
import requests


CLOUDFLARE_ZONE = os.getenv("CLOUDFLARE_ZONE")
CLOUDFLARE_TOKEN = os.getenv("CLOUDFLARE_TOKEN")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


def _send_purge_cache_request(url: str, cloudflare_token: str, urls_to_purge: list):
    with requests.post(
        url=url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cloudflare_token}",
        },
        json={
            "files": urls_to_purge
        }
    ) as resp:
        if resp.status_code == 200:
            print(f"Cache purged for {', '.join(urls_to_purge)}")
        else:
            print(f"Error when purging cache, status: {resp.status_code}, body: {resp.text}")


def _get_tentacles_url(tentacle_url_identifier):
    if not S3_BUCKET_NAME:
        raise RuntimeError("Missing S3_BUCKET_NAME env variable")
    return os.getenv(
        "TENTACLES_URL",
        f"https://{S3_BUCKET_NAME}."
        f"{os.getenv('TENTACLES_OCTOBOT_ONLINE_URL', 'octobot.online')}/"
        f"officials/packages/full/base/"
        f"{tentacle_url_identifier}/"
        f"any_platform.zip"
    )


def clear_cache(tentacle_url_identifiers):
    if not CLOUDFLARE_ZONE:
        raise RuntimeError("Missing CLOUDFLARE_ZONE env variable")
    if not CLOUDFLARE_TOKEN:
        raise RuntimeError("Missing CLOUDFLARE_TOKEN env variable")
    # https://developers.cloudflare.com/api/operations/zone-purge#purge-cached-content-by-url
    url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE}/purge_cache"
    _send_purge_cache_request(
        url,
        CLOUDFLARE_TOKEN,
        [
            _get_tentacles_url(tentacle_url_identifier)
            for tentacle_url_identifier in tentacle_url_identifiers
        ]
    )


if __name__ == '__main__':
    clear_cache(sys.argv[1:])
