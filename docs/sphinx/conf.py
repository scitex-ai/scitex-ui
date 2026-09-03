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
# html_static_path intentionally omitted — there are no custom static
# files in docs/sphinx/_static/, and Sphinx warns about a missing dir
# under -W (treats warnings as errors in CI). Re-add this entry the
# day someone actually drops a custom CSS/JS file there.
# html_static_path = ["_static"]

autodoc_member_order = "bysource"

# `asgiref.sync` does `if TYPE_CHECKING: from _typeshed import ...`, and
# `_typeshed` is a stubs-only module that never exists at runtime — so
# sphinx_autodoc_typehints' guarded-import probe always fails there and warns.
# It fires for ANY module that imports Django, which is why it appeared the day
# `apps` / `context_processors` / `middleware` were first documented rather than
# for anything those modules do.
#
# Scoped to this one category deliberately, in the spirit of the filter above:
# it is a diagnostic about a dependency's type-checking imports, not about our
# doc tree, and nothing on our side can act on it. A blanket `-W` opt-out would
# also hide the project-side warnings this build exists to catch — the two
# malformed docstrings it caught in `branding` and `apps` are exactly that.
suppress_warnings = ["sphinx_autodoc_typehints.guarded_import"]
