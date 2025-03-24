Installation and Usage
=============================


Installation
-----------------------------

You need Python to run Neurotorch. 

.. note:: 
    If you are new to Python and want to install Neurotorch the easiest way possible,
    I recommend the following steps:

    #. Download and install Miniconda from `anaconda.com/download/success <https://www.anaconda.com/download/success>`_. But please make sure to download Miniconda and not Anaconda
    #. Open the Anaconda prompt (On Windows it should show up )
    #. Create a virtual environment to not mess up with your other python packages. To do this, for example type

    .. code-block:: bash

        conda create -n neurotorchmz python pip
    
    This will create a new environment with the name 'neurotorchmz' (you can choose any name you want).
    Now wait (and acknowledge the installtion prompts when asked) and activate your environment when finished by typing

    Execute the following 

    .. code-block:: bash

        conda activate neurotorchmz

To install Neurotorch, type the following inside your virtual environment

.. code-block:: bash

    pip install neurotorchmz

If you want to update to a new version append `--upgrade`

.. code-block:: bash

    pip install neurotorchmz --upgrade

If you want to connect to Fiji/ImageJ, you also need to install OpenJDK and Apache Maven. For OpenJDK i recommend the bundled build from Microsoft 
(`microsoft.com/openjdk <https://www.microsoft.com/openjdk>`_). After installing it, download `Apache maven <https://maven.apache.org/download.cgi>`_ 
and unzip the content into the folder you want to install it to (for example on Windows I use ``C:\\Program Files\\Maven``). Then you need to 
modify the path variable to point to the folder (in my example case that would be ``C:\\Program Files\\Maven\\apache-maven-3.9.9\\bin``). For this I recommend
the following tutorials: 

* `Video 1 <https://www.youtube.com/watch?v=19HZ19FL1v4>`_ 
* `Video 2 <https://www.youtube.com/watch?v=gb9e3m98avk>`_

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


Some notes on RAM usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Please note that Neurotorch is very demanding in terms of RAM usage and can easily exceed 5 times the amount of RAM used
for the same file in Fiji/ImageJ. While on modern system there will be no crashes, it may drastically reduce performance.
Therefore it is recommended to use Neurotorch only on systems with 32 GB of RAM.