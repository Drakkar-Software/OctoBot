#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.

import datetime
import os

from git import Repo

from config import ORIGIN_URL, GIT_ORIGIN

short_version = input("Enter the new short version (R.D.MA_MI) : ")
dev_phase = input("Enter the development phase : ")
full_version = "{0}-{1}".format(short_version, dev_phase)
issues = input("Concerned issues : ")
new_features = input("New features : ")
bug_fix = input("Bug fix : ")

today = datetime.date.today()

changelog_new_lines = "\n" \
                      "Changelog for {0}-{1}\n" \
                      "    ====================\n" \
                      "    *Released date : {2}*\n" \
                      "    # Concerned issues :\n" \
                      "    {3}\n" \
                      "    # New features :\n" \
                      "    {4}\n" \
                      "    # Bug fix :\n" \
                      "    {5} \n".format(short_version,
                                          dev_phase,
                                          today.strftime('%M %d %Y'),
                                          issues,
                                          new_features,
                                          bug_fix)

with open("docs/CHANGELOG.md", "r") as file:
    changelog_lines = file.readlines()

changelog_lines[1] = changelog_new_lines

with open("docs/CHANGELOG.md", "w") as file:
    for line in changelog_lines:
        file.write(line)

# TODO
# - modify __init__.py
# - modify README

repo = Repo(os.getcwd())
repo.commit("{0} {1}".format("[Version] New version ", full_version))
repo.tag(full_version)
origin = repo.create_remote(GIT_ORIGIN, url=ORIGIN_URL)
origin.push()
