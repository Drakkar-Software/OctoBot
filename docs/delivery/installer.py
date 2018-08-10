import glob
import json
import logging
import os

import requests

from config.cst import CONFIG_FILE, PROJECT_NAME, GITHUB_API_CONTENT_URL, GITHUB_REPOSITORY, GITHUB_RAW_CONTENT_URL, \
    VERSION_DEV_PHASE, DEFAULT_CONFIG_FILE, LOGGING_CONFIG_FILE

FOLDERS_TO_CREATE = ["logs"]
FILES_TO_DOWNLOAD = [
    (
        f"{GITHUB_RAW_CONTENT_URL}/cjhutto/vaderSentiment/master/vaderSentiment/emoji_utf8_lexicon.txt",
        "vaderSentiment/emoji_utf8_lexicon.txt"),
    (
        f"{GITHUB_RAW_CONTENT_URL}/cjhutto/vaderSentiment/master/vaderSentiment/vader_lexicon.txt",
        "vaderSentiment/vader_lexicon.txt"),
    (
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{DEFAULT_CONFIG_FILE}",
        CONFIG_FILE
    ),
    (
        f"{GITHUB_RAW_CONTENT_URL}/{GITHUB_REPOSITORY}/{VERSION_DEV_PHASE}/{LOGGING_CONFIG_FILE}",
        LOGGING_CONFIG_FILE
    )
]

GITHUB_LATEST_RELEASE_URL = f"{GITHUB_API_CONTENT_URL}/repos/{GITHUB_REPOSITORY}/releases/latest"

def create_environment():
    logging.info(f"{PROJECT_NAME} is checking your environment...")
    # download files
    for file_to_dl in FILES_TO_DOWNLOAD:
        file_content = requests.get(file_to_dl[0]).text
        directory = os.path.dirname(file_to_dl[1])

        if not os.path.exists(directory) and directory:
            os.makedirs(directory)

        file_name = file_to_dl[1]
        if not os.path.isfile(file_name) and file_name:
            with open(file_name, "w") as new_file_from_dl:
                new_file_from_dl.write(file_content)

    # create folders
    for folder in FOLDERS_TO_CREATE:
        if not os.path.exists(folder) and folder:
            os.makedirs(folder)

    logging.info(f"Your {PROJECT_NAME} environment is ready !")


def update_binary():
    # parse latest release
    try:
        logging.info(f"{PROJECT_NAME} is checking for updates...")
        latest_release_data = json.loads(requests.get(GITHUB_LATEST_RELEASE_URL).text)
        latest_version = latest_release_data["tag_name"]

        octobot_binaries = glob.glob(f'{PROJECT_NAME}*')

        # if current octobot binary found
        if octobot_binaries:
            logging.info(f"{PROJECT_NAME} installation found, analyzing...")

        else:
            download_binary(latest_release_data)

    except Exception as e:
        logging.error(f"Failed to download latest release data : {e}")


def download_binary(latest_release_data):
    binary = latest_release_data["assets"][0]
    r = requests.get(binary["url"], stream=True)
    path = binary["name"]
    with open(path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in progress.bar(r.iter_content(chunk_size=1024), expected_size=(total_length / 1024) + 1):
            if chunk:
                f.write(chunk)
                f.flush()


def update_tentacles():
    pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    create_environment()
    update_binary()
    update_tentacles()
    # TODO install tentacles
