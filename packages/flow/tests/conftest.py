# in conftest.py to load the .env file before any test is run or any import is done

import dotenv
dotenv.load_dotenv(dotenv_path="tests/.env")
