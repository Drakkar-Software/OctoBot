import sys

print("", sys.path[-1], "", sep="\n" + "-" * 80 + "\n")

# -- Project information -----------------------------------------------------

project = "OctoBot"
copyright = "2021, DrakkarSoftware"
author = "DrakkarSoftware"

# The short X.Y version
version = '0.4.0b2'

# The full version, including alpha/beta/rc tags
release = '0.4.0-beta2'

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
