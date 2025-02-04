from . import Start, Edition
import sys
if __name__ == "__main__":
    if "NEUROTORCH_DEBUG" in sys.argv:
        Start(Edition.NEUROTORCH_DEBUG)
    else:
        Start()