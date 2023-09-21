import importlib.metadata

project = "stac-task"
copyright = "2023 Element 84"
author = "Matt Hanson, Pete Gadomski"
release = importlib.metadata.version("stac-task")

extensions = [
    "nbsphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx_click",
    "sphinxcontrib.autodoc_pydantic",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_theme_options = {"github_url": "https://github.com/stac-utils/stac-task"}

intersphinx_mapping = {
    "pystac": ("https://pystac.readthedocs.io/en/stable", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

nbsphinx_custom_formats = {".md": "jupytext.reads"}
