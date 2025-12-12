# Configuration file for the Sphinx documentation builder.

import os
import sys
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.abspath("../.."))  # Source code dir relative to this file

# -- Project information

project = "STAC Task"
copyright = f"{datetime.now().year}, Element 84, Inc."


def get_latest_tag() -> str:
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except:
        return "0.0.0"


release = get_latest_tag()
version = release

# -- General configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]

autosummary_generate = True  # Turn on sphinx.ext.autosummary

templates_path = ["_templates"]

# -- Options for HTML output

html_theme = "sphinx_rtd_theme"

# -- Options for EPUB output
epub_show_urls = "footnote"
