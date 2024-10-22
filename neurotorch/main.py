import sys, os
if __name__ == "__main__":
    neurotorch_path = os.path.join(os.path.join(__file__, os.pardir), os.pardir)
    neurotorch_path = os.path.abspath(neurotorch_path)
    sys.path.insert(1, neurotorch_path)

import neurotorch
neurotorch.Start()