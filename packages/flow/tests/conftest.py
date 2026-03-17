# in conftest.py to load the .env file before any test is run or any import is done

import dotenv
import os
dotenv.load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
