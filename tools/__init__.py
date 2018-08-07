import logging
import sys

MIN_PYTHON_VERSION = (3, 6)

# check python version
current_version = sys.version_info
if not current_version >= MIN_PYTHON_VERSION:
    logging.error(" OctoBot requires Python version to be higher or equal to Python " + str(MIN_PYTHON_VERSION[0])
                  + "." + str(MIN_PYTHON_VERSION[1]) + " current Python version is " + str(current_version[0])
                  + "." + str(current_version[1]) + "\n"
                  + "You can download Python last versions on: https://www.python.org/downloads/")
    sys.exit(-1)

# binary tentacle importation
sys.path.append(os.path.dirname(sys.executable))

# if compatible version, can proceed with imports
