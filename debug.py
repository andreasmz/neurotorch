# This file is intended to start Neurotorch in Debugging mode
#
# © Andreas Brilka 2024-2025
#


import os
os.environ["NEUROTORCH_DEBUG"] = "True"

import neurotorchmz
from neurotorchmz import Edition
neurotorchmz.start(Edition.NEUROTORCH_DEBUG)