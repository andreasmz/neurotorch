<p align="center">
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/docs/media/neurotorch_coverimage.jpeg" style="max-width: 600px;">
</p> 

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fandreasmz%2Fneurotorch%2Fmain%2Fpyproject.toml&style=flat&logo=Python&label=Python)
![Package version from PyPI package](https://img.shields.io/pypi/v/neurotorchmz?style=flat&logo=pypi&label=PyPI%20Package%20Version&color=09bd2d&link=https%3A%2F%2Fpypi.org%2Fproject%2FNeurotorchmz%2F)
![PyProject.toml](https://img.shields.io/badge/dynamic/toml?url=https%3A%2F%2Fraw.githubusercontent.com%2Fandreasmz%2Fneurotorch%2Fmain%2Fpyproject.toml&query=%24.project.classifiers%5B1%5D&label=PyProject.toml&color=yellow)
![License from PyPI package](https://img.shields.io/pypi/l/neurotorchmz?style=flat&logo=creativecommons&color=fc030f&link=https%3A%2F%2Fgithub.com%2Fandreasmz%2Fneurotorch%2Fblob%2Fmain%2FLICENSE
)

![GitHub Actions build.yml Status](https://img.shields.io/github/actions/workflow/status/andreasmz/neurotorch/build.yml?style=flat&label=build&link=https%3A%2F%2Fgithub.com%2Fandreasmz%2Fneurotorch%2Factions%2Fworkflows%2Fbuild.yml)
![GitHub Actions documentation.yml Status](https://img.shields.io/github/actions/workflow/status/andreasmz/neurotorch/documentation.yml?style=flat&label=build%20(docs)&link=https%3A%2F%2Fgithub.com%2Fandreasmz%2Fneurotorch%2Factions%2Fworkflows%2Fdocumentation.yml)


<span style="color:red;">Please note</span>: There is another project called neurotorch on GitHub/PyPI not related to this project. To avoid mix-up, the package is named _neurotorchmz_ with the _mz_ as a refrence to Mainz where the software was developed.

# Neurotorch

Neurotorch is a tool designed to extract regions of synaptic activity in neurons tagges with iGluSnFR, but is in general capable to find any kind of local brightness increase due to synaptic activity. It works with microscopic image series / videos and is able to open an variety of formats (for details see below)
- **Fiji/ImageJ**: Full connectivity provided. Open files in ImageJ and send them to Neurotorch and vice versa.
- **Stimulation extraction**: Find the frames where stimulation was applied
- **ROI finding**: Auto detect regions with high synaptic activity. Export data directly or send the ROIs back to ImageJ
- **Image analysis**: Analyze each frame of the image and get a visual impression where signal of synapse activity was detected
- **API**: You can access the core functions of Neurotorch also by importing it as an python module

### Installation

<a href="https://github.com/andreasmz/neurotorch/releases/latest/download/neurotorchmz-windows-latest-x64.zip" target="_blank">
  <img src="https://img.shields.io/badge/Download-Windows-blue?style=for-the-badge&logoColor=white" alt="Download Windows">
</a>
<a href="https://github.com/andreasmz/neurotorch/releases/latest/download/neurotorchmz-macos-latest-x64.zip" target="_blank">
  <img src="https://img.shields.io/badge/Download-macOS-blue?style=for-the-badge&logo=apple&logoColor=white" alt="Download macOS">
</a>
<a href="https://github.com/andreasmz/neurotorch/releases/latest/download/neurotorchmz-ubuntu-latest-x64.zip" target="_blank">
  <img src="https://img.shields.io/badge/Download-Linux%20x86--64-blue?style=for-the-badge&logo=linux&logoColor=white" alt="Download Linux (64bit)">
</a>

Neurotorch can be downloaded in a standalone, portable version for Windows and MacOS. The download comes with a compatible Python environment containing all necessary dependencies. Please note that Fiji/ImageJ as well as TraceSelector are not included in the build. However Neurotorch is able to automatically install them once you want to use them.

### Installation for advanced users 

If you already have Python installed, you can also install it via pip as a very small (~ 1 MB) package:
```bash
pip install neurotorchmz
```
This approach is the recommended way if you are familiar with Python as it minimizes the overhead of downloading and storing Python multiple times. It is recommened to use a virtual environment manager like [miniconda](https://docs.anaconda.com/miniconda/). Please refer to the [documentation](https://andreasmz.github.io/neurotorch/introduction/installation/) for more details.

If you want to use the Fiji/ImageJ bridge you will need to install OpenJDK and Apacha maven and add them to your system PATH. While Neurotorch is able to install those for you into your AppData folder, you can also install them manually from [openjdk.org](https://openjdk.org/) and [maven.apache.org](https://maven.apache.org/download.cgi)

To run Neurotorch, type
```bash
python -m neurotorchmz
```
You can create a shortcut on your Desktop where you replace the command python with the path to your python executable.

If you want to interact with Neurotorch you can import it as an module
```python
import neurotorchmz
session = neurotorchmz.start_background(headless=False)
```

To update your installation, type
```bash
pip install neurotorchmz --upgrade
```

### Documentation

<a href="https://andreasmz.github.io/neurotorch/" target="_blank">
  <img src="https://img.shields.io/badge/Documentation-blue?style=for-the-badge&logo=read-the-docs&logoColor=white" alt="Documentation">
</a>

You can find the full documentation under [andreasmz.github.io/neurotorch](https://andreasmz.github.io/neurotorch/).

### About / Citation

Neurotorch was developed at the AG Heine (Johannes Gutenberg Universität, Mainz/Germany) and is currently under active development.


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
    <img src="https://raw.githubusercontent.com/andreasmz/neurotorch/main/docs/media/nt/tab_roifinder/tab_roifinder.png" style="max-width: 600px;"> <br>
    <em>Extraction of regions with high synaptic activity. For the choosen image with good enough signal to noise ratio, all settings were determined automatically by the program and nothing more than pressing 'Detect' was necessary to get this screen. The ROIs are marked in the images with red boundaries while the selected ROI displayed also with the mean value over time is marked with yellow boundaries</em>
</p> 