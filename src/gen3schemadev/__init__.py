# Expose main submodules for convenient import
from .schema import *
from .validators import *
from .cli import *
from .utils import *
from .converter import *
from .ddvis import *

try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    from importlib_metadata import version, PackageNotFoundError  # for Python<3.8

try:
    from importlib.metadata import version
    __version__ = version('gen3schemadev')
except Exception:
    __version__ = 'unknown'