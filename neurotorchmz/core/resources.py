""" Provides a utility library to load resources and strings """
import json
from PIL import Image

from . import settings
from .logs import logger

with open(settings.resource_path / "strings.json") as f:
    _json = json.load(f)

def get_string(path:str) -> str:
    """ Retreive a key by supplying the adress with slashes (example: tab2/algorithms/diffMax). Returns '' if the key is not found and the path itself if it does not point to a end node """
    _folder = _json
    paths = path.split("/")
    for i, key in enumerate(paths):
        if key not in _folder.keys():
            logger.warning(f"Can't find key {path}. It stops at '{'/'.join(paths[0:i])}'")
            return ""
        _folder = _folder[key]
    if type(_folder) == str:
        return _folder
    return path

def get_image(filename: str) -> Image.Image:
    """ Open a image. Raises FileNotFoundError if the file can't be opened """
    path = settings.resource_path / filename
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Can't find the resource file {filename}")
    return Image.open(path)
