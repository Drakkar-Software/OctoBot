import os
import json
import re
from urllib.request import urlopen


def remove_special_chars(input_string):
    return re.sub(r'[^a-zA-Z0-9_]', '', input_string)


def fetch_container_metadata(container_metadata_url, enpoint="taskWithTags"):
    with urlopen(container_metadata_url + "/" + enpoint) as response:
        body = response.read()
    return json.loads(body)


def write_dotenv(tags, dotenv_path=os.getenv("DOTENV_PATH", os.path.curdir)):
    with open(os.path.join(dotenv_path, ".env"), 'w') as env_file:
        for key, value in tags.items():
            env_file.write(remove_special_chars(key) + "=" + value+"\n")


def load_env_from_tag():
    # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint-v4.html
    container_metadata_url = os.getenv("ECS_CONTAINER_METADATA_URI_V4", None)
    if container_metadata_url is not None:
        try:
            container_metadata = fetch_container_metadata(container_metadata_url)
            write_dotenv(container_metadata.get('TaskTags', {}))
        except Exception as e:
            print("Error when requesting or parsing aws metadata")


if __name__ == '__main__':
    load_env_from_tag()
