import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Tuple, Union

    VERSION_TUPLE = Tuple[Union[int, str], ...]
else:
    VERSION_TUPLE = object

version: str
__version__: str
__version_tuple__: VERSION_TUPLE
version_tuple: VERSION_TUPLE

__version__ = version = '0.0.1'
__version_tuple__ = version_tuple = tuple(map(int, version.split('.')))

# FIXME: remove this after pymupdf updates swig to >=4.4.0 - https://github.com/swig/swig/issues/3279
warnings.filterwarnings(
    'ignore',
    category=DeprecationWarning,
    message=r'.*swig.*__module__.*',
)
