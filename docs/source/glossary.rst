Glossary
========

.. glossary::

    Difference Image:
        The so called difference image (shortened to *diff image* or *diff img*) is actually a misleading term, as it actually has a time 
        dimension and refers to the difference between each frame of the input video.
        If for example your microscopic video has dimension w x h x t, the diff image has the dimension w x h x (t-1). It is the core feature of
        Neurotorch and mostly used for the detection algorithms.