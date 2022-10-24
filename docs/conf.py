import sys
import os
# sys.path.insert(0, os.path.abspath('../src/abstractclient/defaultpipeline'))
print()
print(sys.path)
print()

# General configuration
# ---------------------
extensions = ['sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    'sphinxcontrib.plantuml',
    'sphinx.ext.githubpages']

# General substitutions.
project = 'Abstract Client'
copyright = 'Sergo Tsitsiashvili'

# The default replacements for |version| and |release|.
#
# The short X.Y version.
version = '1.3.0'

master_doc = 'index'
html_static_path = ['static']
plantuml = 'java -jar /usr/share/plantuml/plantuml.jar'

# Theme Alabaster configuration
html_theme = 'alabaster'
html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html"
    ]
}

html_theme_options = {
    "logo": "pipeline.png",
    "logo_name": True,
    "description": "Абстрактный клиент потоков данных",
    "fixed_sidebar": True,
    "tidelift_url": "https://tidelift.com/subscription/pkg/pypi-alabaster?utm_source=pypi-alabaster&utm_medium=referral&utm_campaign=docs",  # noqa
}

# Show module name without paths
add_module_names = False
# Both the class’ and the __init__ method’s docstring are concatenated and inserted.
autoclass_content = 'both'

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_custom_sections = None