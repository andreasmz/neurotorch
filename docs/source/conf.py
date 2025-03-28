# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(1, str(_nt_path := Path("").resolve().parent.parent.resolve()))
print(f"Importing NeurotorchMZ from {_nt_path}")
import neurotorchmz

project = 'NeurotorchMZ'
copyright = f'© {datetime.now().year}, Andreas Brilka'
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
]

print(f"Generating documentation for neurotorchmz version {neurotorchmz.__version__}")

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_favicon = '../media/neurotorch_logo.ico'