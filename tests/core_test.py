import pytest
import logging

import neurotorchmz

session = neurotorchmz.Session(neurotorchmz.Edition.NEUROTORCH_DEBUG)

def test_path():
    assert "git" in str(neurotorchmz.__path__).lower()
