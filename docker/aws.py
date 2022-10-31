import os
import json
import re
from urllib.request import urlopen


def remove_special_chars(input_string):
    return re.sub(r'[^a-zA-Z0-9_]', '', input_string)


if __name__ == '__main__':
    # https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint-v4.html
    container_metadata_url = os.getenv("ECS_CONTAINER_METADATA_URI_V4", None)
    dotenv_path = os.getenv("DOTENV_PATH", os.path.curdir)
    if container_metadata_url is not None:
        try:
            with urlopen(container_metadata_url + "/taskWithTags") as response:
                body = response.read()
            container_metadata = json.loads(body)
            with open(os.path.join(dotenv_path, ".env"), 'w') as env_file:
                for key, value in container_metadata['TaskTags'].items():
                    env_file.write(remove_special_chars(
                        key) + "=" + value+"\n")
        except Exception as e:
            print("Error when requesting or parsing aws metadata")
