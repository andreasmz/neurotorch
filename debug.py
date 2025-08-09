import os
os.environ["NEUROTORCH_DEBUG"] = "True"

import neurotorchmz
from neurotorchmz import Edition
neurotorchmz.start(Edition.NEUROTORCH_DEBUG)