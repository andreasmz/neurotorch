from typing import Self
import pickle

class DeserializeError(Exception):
    pass

class SerializeError(Exception):
    pass

class Serializable:
    """
        Abstract base class for objects that are serializable
    """
    # Dev Note: Still in an early development stage

    def pickle(self, **kwargs) -> bytes:
        """ Pickles the object and returns it as a binary string"""
        return pickle.dumps(self.serialize(**kwargs))

    def load_pickle(self, b: bytes) -> Self:
        """ Decodes a pickle object """
        return self.deserialize(pickle.loads(b))

    def serialize(self, **kwargs) -> dict:
        """ Serialize the current class object into a dict """
        raise NotImplementedError()

    @classmethod
    def deserialize(cls, serialize_dict: dict, **kwargs) -> Self:
        """ Deserialize the given dict into a class object """
        raise NotImplementedError()
    
