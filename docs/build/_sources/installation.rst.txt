Installation and Usage
=============================


Installation
-----------------------------

You need Python to run Neurotorch. 

.. note:: 
    If you are new to Python and want to install Neurotorch the easiest way possible,
    I recommend the following steps:

    #. Download and install Miniconda from `anaconda.com/download/success <https://www.anaconda.com/download/success>`_. But please make sure to download Miniconda and not Anaconda
    #. Open the Anaconda prompt (For example on Windows you can search it after pressing the windows button)
    #. I strongly recommend to create a virtual enviorenment to not mess up with your other python packages. To do this, for example type

    .. code-block:: bash

        conda create -n neurotorchmz python pip
    
    This will create a new enviorenment with the name 'neurotorchmz' (you can choose any name you want).
    Now wait (and acknowledge the installtion prompts when asked) and activate your enviorenment when finished by typing

    .. code-block:: bash

        conda activate neurotorchmz

To install, simply type

.. code-block:: bash

    pip install neurotorchmz

If you want to update to a new version append `--upgrade`

.. code-block:: bash

    pip install neurotorchmz --upgrade

Also, you need to install OpenJDK and Apache Maven to run PyImageJ. An easy solution is to use the bundled Build from Microsoft you can find under 
`microsoft.com/openjdk <https://www.microsoft.com/openjdk>`_

Usage
-----------------------------

To run Neurotorch, type

.. code-block:: bash

    python -m neurotorchmz

You can also import it as a module to access the API

.. code-block:: python3

    import neurotorchmz
    print(neurotorchmz.__version__)
    neurotorchmz.Start_Background()

I recommend to create a shortcut on your Desktop where you replace the command python with the path to your python executable. 
