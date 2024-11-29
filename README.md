<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/doc/media/neurotorch_coverimage_24_11.jpeg" style="max-width: 600px;">
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

You need python to run Neurotorch. Also it is recommended to create a virtual enviorenment to not mess up with your other python packages, for example using [miniconda](https://docs.anaconda.com/miniconda/). When inside your virtual enviorenment, simply type
```bash
pip install neurotorchmz
```
Also, you need to install OpenJDK and Apache Maven to run PyImageJ. An easy solution is to use the bundled Build from Microsoft you can find [here](https://www.microsoft.com/openjdk)

To update your installation, type
```bash
pip install neurotorchmz --upgrade
```

### Documentation

There is [neurotorch_documentation.pdf](https://raw.githubusercontent.com/andreasmz/neurotorch/main/doc/neurotorch_documentation.pdf) on the GitHub repository, but you can also access it from inside Neurotorch on the tab 'Welcome to Neurotorch'

### About

Neurotorch was developed at the AG Heine (Johannes Gutenberg Universität, Mainz/Germany) and is currently under active development.

### Development roadmap

Currently in active development:
- [x] **released** Integration of plugins: Rather than providing an direct binding to TraceSelector, it will be implemented as a plugin
- [x] New ROI finding algorithm based on local maxima

Ideas for future releases:
- [ ] Synapse analysis tab: Same algorithm as in the Synapse ROI finder, but for each signal frame separately



### Impressions
Please note: Neurotorch is under continuous development. Therefore the visuals provided here may be outdated in future versions.

<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/doc/media/readme/neurotorch_tabImage_01.png" style="max-width: 600px;"> <br>
    <em>First impression of an file opened in Neurotorch. For specific file formats (here nd2), a variety of metadata can be extracted</em>
</p> 
<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/doc/media/readme/neurotorch_tabSignal_01.png" style="max-width: 600px;"> <br>
    <em>Use the tab 'Signal' to find the timepoints with stimulation (marked in the plot on the left site with yellow dots). You can also use this tab to view the video frame by frame</em>
</p> 
<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/doc/media/readme/neurotorch_tabROIFinder_01.png" style="max-width: 600px;"> <br>
    <em>Extraction of regions with high synaptic activity. For the choosen image with good enough signal to noise ratio, all settings were determined automatically by the program and nothing more than pressing 'Detect' was necessary to get this screen. The ROIs are marked in the images with red boundaries while the selected ROI displayed also with the mean value over time is marked with yellow boundaries</em>
</p> 

### Release notes

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
