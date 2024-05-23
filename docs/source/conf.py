# Configuration file for the Sphinx documentation builder.

import os
import sys

sys.path.insert(
    0, os.path.abspath("../../src")
)  # Source code dir relative to this file

# -- Project information

project = "STAC Task"
copyright = "2021, Element 84, Inc."

release = "0.5"
version = "0.5.1"

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
