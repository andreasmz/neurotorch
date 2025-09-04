# This file is intended to be used with pyinstaller to bundle the project.
#
# © Andreas Brilka 2024-2025
#


import os
os.environ["NEUROTORCH_PORTABLE"] = "True"

import neurotorchmz
neurotorchmz.start()