#  Drakkar-Software OctoBot-Interfaces
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

import os
import webbrowser


def open_in_background_browser(url):
    """
    Uses webbrowser.open(url) but skips non-background browsers as they are blocking the current process,
    we don't want that.
    Warning: should be called before any other call to webbrowser otherwise default browser discovery
    (including non-background browsers) will be processed by webbrowser
    """
    # env var used to identify console browsers, which are not background browsers
    term_var = "TERM"
    prev_val = None
    if term_var in os.environ:
        prev_val = os.environ[term_var]
        # unsetting it skips console browser discovery
        os.environ[term_var] = ""
    try:
        webbrowser.open(url)
    finally:
        if prev_val is not None:
            # restore env variable
            os.environ[term_var] = prev_val
