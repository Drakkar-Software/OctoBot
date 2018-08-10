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

if __name__ == '__main__':
    logger = logging.getLogger(f"{PROJECT_NAME} Installer")

    logger.info(f"is checking your environment...")
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

    # parse latest release
    try:
        latest_release_data = json.loads(requests.get(GITHUB_LATEST_RELEASE_URL).text)
        pass
    except Exception as e:
        logger.error(f"Failed to download latest release data : {e}")

    # TODO install tentacles
