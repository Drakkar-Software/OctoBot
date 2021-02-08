import os
import sys

import octobot.constants as constants

PATH_HERE = os.path.abspath(os.path.dirname(__file__))
PATH_ROOT = os.path.join(PATH_HERE, "..", "..")
sys.path.insert(0, os.path.abspath(PATH_ROOT))

# -- Project information -----------------------------------------------------

project = constants.PROJECT_NAME
copyright = f"2021, {constants.AUTHOR}"
author = constants.AUTHOR

# The short X.Y version
version = constants.VERSION

# The full version, including alpha/beta/rc tags
release = constants.LONG_VERSION

# -- Extensions --------------------------------------------------------------
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
]

# -- Options for HTML output -------------------------------------------------

html_title = project

# NOTE: All the lines are after this are the theme-specific ones. These are
#       written as part of the site generation pipeline for this project.
# !! MARKER !!
html_theme = "asteroid_sphinx_theme"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_logo = "_static/images/favicon.ico"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    "canonical_url": "https://github.com/Drakkar-Software/OctoBot",
    "collapse_navigation": False,
    "display_version": True,
    "logo_only": False,
}

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
# source_suffix = ['.rst', '.md', '.ipynb']
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    # '.md': 'markdown',
    ".ipynb": "nbsphinx",
}
