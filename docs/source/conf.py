# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os

os.environ.pop("DISPLAY", None)  # DISPLAY löschen

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(1, str(_nt_path := Path("").resolve().parent.parent.resolve()))
print(f"Importing NeurotorchMZ from {_nt_path}")
import neurotorchmz
from neurotorchmz.gui import window # Necessary as neurotorch window is not auto imported

project = 'NeurotorchMZ'
copyright = f'© 2024-{datetime.now().year}, Andreas Brilka'
author = neurotorchmz.__author__
release = neurotorchmz.__version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []

master_doc = "index"

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
]

autosummary_generate = True

autodoc_default_options = {
    'members': True,                 # shows methods/attributs
    'undoc-members': True,          # shows also methods without docstring
    'private-members': True,
    'show-inheritance': True,
    'inherited-members': False,     
}

print(f"Generating documentation for neurotorchmz version {neurotorchmz.__version__}")

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_book_theme'
html_favicon = '../media/neurotorch_logo.ico'