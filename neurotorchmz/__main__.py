from . import start, Edition
import sys
if __name__ == "__main__":
    if "NEUROTORCH_DEBUG" in sys.argv:
        start(Edition.NEUROTORCH_DEBUG)
    else:
        start()