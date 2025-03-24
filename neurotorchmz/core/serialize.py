from abc import ABC, abstractmethod
from typing import Self, Any
import base64

class Serializable(ABC):
    """
        Serialize objects
    """

    def __init__(self):
        super().__init__()

    def serialize_encode_base64(self, obj: Any) -> str:
        """ Pickles the object and returns it as base64 str """

    def serialize_decode_base64(self, s: str) -> str:
        """ Decodes a pickled and base64 encoded object """
        b = base64.encode(s)


    @abstractmethod
    def serialize(self, **kwargs) -> dict:
        raise NotImplementedError()

    @abstractmethod
    def deserialize(self, serialize_dict: dict, **kwargs):
        raise NotImplementedError()
    
