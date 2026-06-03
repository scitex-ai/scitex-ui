"""Sphinx configuration for scitex-ui documentation."""

# Silence the sphinx_autodoc_typehints internal deprecation that triggers
# a RemovedInSphinx10Warning under sphinx-build -W. The deprecation is in
# the third-party extension (set_application call against a deprecated
# Sphinx internal API), not in our doc tree, so suppressing it does not
# hide any project-side problem.
import warnings

try:
    from sphinx.deprecation import RemovedInSphinx10Warning

    warnings.filterwarnings(
        "ignore",
        category=RemovedInSphinx10Warning,
        module=r"sphinx_autodoc_typehints\..*",
    )
except ImportError:
    pass

project = "scitex-ui"
copyright = "2024-2026, Yusuke Watanabe"
author = "Yusuke Watanabe"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

autodoc_member_order = "bysource"
