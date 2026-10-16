"""Bodega: keep track of your gear, put it in packages, rent it out."""

__version__ = "1.3.0"
APP_NAME = "Bodega"


def version_label() -> str:
    """The version as people see it: "1.3.0", or for a build "1.3.0 (a1b2c3d)", the commit it was made from."""
    from bodega._build import COMMIT

    return f"{__version__} ({COMMIT})" if COMMIT else __version__
