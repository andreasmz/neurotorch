<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/docs/media/neurotorch_coverimage.jpeg" style="max-width: 600px;">
</p> 

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fandreasmz%2Fneurotorch%2Fmain%2Fpyproject.toml&style=flat&logo=Python)
![Dynamic TOML Badge](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fandreasmz%2Fneurotorch%2Fmain%2Fpyproject.toml&query=%24.project.version&style=flat&label=Version&color=09bd2d)
![Dynamic TOML Badge](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fandreasmz%2Fneurotorch%2Fmain%2Fpyproject.toml&query=%24.project.classifiers%5B1%5D&label=PyProject.toml&color=yellow)

<span style="color:red;">Please note</span>: There is another project called neurotorch on GitHub/PyPI not related to this project. To avoid mix-up, the package is named _neurotorchmz_ with the _mz_ as a refrence to Mainz where the software was developed.

# Neurotorch

Neurotorch is a tool designed to extract regions of synaptic activity in neurons tagges with iGluSnFR, but is in general capable to find any kind of local brightness increase due to synaptic activity. It works with microscopic image series / videos and is able to open an variety of formats (for details see below)
- **Fiji/ImageJ**: Full connectivity provided. Open files in ImageJ and send them to Neurotorch and vice versa.
- **Stimulation extraction**: Find the frames where stimulation was applied
- **ROI finding**: Auto detect regions with high synaptic activity. Export data directly or send the ROIs back to ImageJ
- **Image analysis**: Analyze each frame of the image and get a visual impression where signal of synapse activity was detected
- **API**: You can access the core functions of Neurotorch also by importing it as an python module

### Installation

You need Python to run Neurotorch. Also it is recommended to create a virtual enviorenment to not mess up with your other python packages, for example using [miniconda](https://docs.anaconda.com/miniconda/). When inside your virtual enviorenment, simply type
```bash
pip install neurotorchmz
```
Also, you need to install OpenJDK and Apache Maven to run PyImageJ. An easy solution is to use the bundled Build from Microsoft you can find [here](https://www.microsoft.com/openjdk)

To run Neurotorch, type
```bash
python -m neurotorchmz
```
I recommend to create a shortcut on your Desktop where you replace the command python with the path to your python executable. You can also import it as an module to use it's API
```python
import neurotorchmz
print(neurotorchmz.__version__)
neurotorchmz.Start_Background()
```

To update your installation, type
```bash
pip install neurotorchmz --upgrade
```

### Documentation

You can find the full documentation under [andreasmz.github.io/neurotorch](https://andreasmz.github.io/neurotorch/).

### About

Neurotorch was developed at the AG Heine (Johannes Gutenberg Universität, Mainz/Germany) and is currently under active development.

### Development roadmap

Currently in active development:
- [x] **Released**: Integration of plugins: Rather than providing an direct binding to TraceSelector, it will be implemented as a plugin
- [x] **Released**: New ROI finding algorithm based on local maxima
- [x] **Preview**: Synapse analysis tab: Same algorithm as in the Synapse ROI finder, but for each signal frame separately



### Impressions
Please note: Neurotorch is under continuous development. Therefore the visuals provided here may be outdated in future versions.

<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/docs/media/nt/tab_image/tab_image.png" style="max-width: 600px;"> <br>
    <em>First impression of an file opened in Neurotorch. For specific file formats (here nd2), a variety of metadata can be extracted</em>
</p> 
<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/docs/media/nt/tab_signal/tab_signal.png" style="max-width: 600px;"> <br>
    <em>Use the tab 'Signal' to find the timepoints with stimulation (marked in the plot on the left site with yellow dots). You can also use this tab to view the video frame by frame</em>
</p> 
<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/docs/media/nt/tab_roifinder/tab_roifinder" style="max-width: 600px;"> <br>
    <em>Extraction of regions with high synaptic activity. For the choosen image with good enough signal to noise ratio, all settings were determined automatically by the program and nothing more than pressing 'Detect' was necessary to get this screen. The ROIs are marked in the images with red boundaries while the selected ROI displayed also with the mean value over time is marked with yellow boundaries</em>
</p> 

### Release notes

>### 25.2.3 (05.02.2025):
>- **Experimental**: Added surface plot of Multiframe Synapses to Synapse Analyzer Tab.

>### 25.2.2 (03.02.2025):
>- **ImageJ/Fiji Bugfix**: Quickfix for a bug exporting ROIs to ImageJ.
>- **Debug mode**: Added possibility to start Neurotorch in debugging mode (for example to test new features) when running as module.

>### 25.2.1 (03.02.2025):
>- **Synapse Analyzer Tab (Preview)**: Added a tab to find multiframe synapses (= different ROIs for each signal frame). This allows the analysis of the movement of a synapse (Plots will be added in a future release).
>- **New ROI Listview**: Complete rewrite of the treeview element for displaying synapses/ROIs. Instead of the (ugly) list of buttons below, now all functionality has been moved to a right-click context menu. The new design architecture allows to keep the position in the list even after removing/adding synapses and offers better generalization and performance. NOTE: To access the tab, set your Neurotorch version to 'NEUROTORCH_DEBUG'.
>- **Logging**: Started the first steps to implement a proper logging system to catch errors much earlier in the future.

>### 24.12.5 (12.12.2024):
>- **Documentation**: Included the new documentation in the build

>### 24.12.3 and 24.12.4 (05.12.2024):
>- **Bugfix**: Minor bugfix on exporting as CSV and fixing importing ROIs from ImageJ

>### 24.12.2 (05.12.2024):
>- **Import ROIs from ImageJ**: Now you can import ROIs from Fiji/ImageJ
>- **Select ROIs by clicking on them**: When clicking into the plot of the ROI Finder tab, the nearest ROI will now be selected
>- **Added ROI Stage**: Now it is possible to keep some or all detected ROIs in the ROI Finder tab on a stage where they won't be cleared on redetecting on loading a new image
>- **Custom ROI names**: Now ROIs can have custom names. Use the button 'Reset Name' to remove custom names
>- **Trace Selector**: The filename is now carried over when exporting into TraceSelector
>- **Code improvements**: Better handling of the Tab ROI Finder Invalidation Events; New Button layout on the same tab
>- **Bugfixes**: names and PIMS metadata were cleared when opening an image; Fixed some wrong checks for empty ImageObjects; Some crashes on exporting as CSV


>### 24.12.1 (29.11.2024)
>- **Sorting by signal strength**: Added the ability to sort by signal strength in local max algorithm. Also added the option to filter for a minimum signal strength
>- **Circular ROI**: Added region props for circular ROIs in local max algorithm. Also changed the definition of a circle with radius r to be equivalent with ImageJ
>- **Added image filters**: Added the ability for image filters and included as first the option to use img - mean(img) instead of imgDiff for detection
>- **Minor changes**: Bugfixes (usage of numpy.empty, trace selector filedialog, matplotlib backend setting...) and improvement of speed (for example slicing the image)

>### 24.11.7 (27.11.2024)
>- **New API**: Better integration of the API
>- **Bugfixes**: Fixing bug in ImageJ Implementation

>### 24.11.6 (27.11.2024)
>- **New detection algorithm**: Added the Local Maximum Algorithm with much better performance than 
>- **GUI**: Massively improved the GUI settings by applying a consistent layout
>- **Detection Algorithms**: Complete rewrite of the detection algorithms integration and adjusting of some parameters
>- **New Tooltip feature**: Introduced tooltips and a new libary to handle string ressources in Neurotorch
>- **Normalized Std, Mean and Median**: By default, for ROI detection now normalized values are used
>- **Colorbar**: Added colorbar to all plots
>- **Improved signal removing**: Fixed and improved some inconsistencies creating the imgDiff
>- **Image Source**: Now for all algorithms the image source can be selected (not just Hysteresis Thresholding)
>- **Massive code review**: Massive review of code and improved stability, for example event system, image loading or Tab ROIFinder plotting


>### 24.11.5 (21.11.2024)
>- **Bugfix** The documentation was not included properly

>### 24.11.4 (21.11.2024)
>- **Introduction of Plugins**: Added the ability to add plugins to neurotorch and introduced TraceSelector as preinstalled plugin
>- **Cache**: Added 'Clear cache' option to denoise menu
>- **Various bugfixes**
