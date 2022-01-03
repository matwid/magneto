
# MAGNETO: Magnetic field measurments to the moon


The *bio magnetic signal detection project* provides the measurement software for detecting signal with an QSPIN OPM conducted at Center of Applied Quantum Technology at University of Stuttgart, Germany.

![GUI screenshot](img/screenshot.png "The graphical user interface.")

## ToDo

- get rid of enthought gui and move to QT


## Pre-Requisites

Some NI measurement Card

## Install

0. Install Microsoft Visual Studio Build Tools with VC C++ 14.0 or greater (https://visualstudio.microsoft.com/de/visual-cpp-build-tools/)
1. get [Miniconda3](https://docs.conda.io/en/latest/miniconda.html)
2. [Windows Only] start Anaconda Powershell 
3. within Anaconda Powershell navigate cloned git folder EPR
4. conda env create -f conda_epr.yml
5. *optional* pip install pillow, nidaqmx, fonttools, enable, chaco, wxPython, pandas


## Run

1. open conda shell
2. source activate epr *or* conda activate epr *or* activate epr
3. ipython
4. run epr.py

## Troubleshooting

Make sure Python 3.7.9 is installed
The most critical package is: enable. Make sure MVC is installed - step 0 above.

