"""EPR startup script"""
import os
import inspect
from traits.api         import HasTraits, Instance, SingletonHasTraits, Range, on_trait_change
from traitsui.api       import View, Item, Group, HGroup, VGroup
from traits.api         import Button
import logging, logging.handlers


#path = os.path.dirname(inspect.getfile(inspect.currentframe()))
path = os.getcwd()
print(path)
# First thing we do is start the logger
#file_handler = logging.handlers.TimedRotatingFileHandler(path+'/log/log.txt', 'W6') # start new file every sunday, keeping all the old ones
file_handler = logging.handlers.TimedRotatingFileHandler(path+'/log/log.txt', 'W6') # start new file every sunday, keeping all the old ones
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(module)s.%(funcName)s - %(levelname)s - %(message)s"))
file_handler.setLevel(logging.DEBUG)
stream_handler=logging.StreamHandler()
stream_handler.setLevel(logging.INFO) # we don't want the console to be swamped with debug messages
logging.getLogger().addHandler(file_handler)
logging.getLogger().addHandler(stream_handler) # also log to stderr
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().info('Starting logger.')

# start the JobManager
"""
from tools import emod
emod.JobManager().start()
"""
# start the CronDaemon
from tools import cron
cron.CronDaemon().start()

# define a shutdown function
from tools.utility import StoppableThread
import threading

def shutdown(timeout=1.0):
    """Terminate all threads."""
    cron.CronDaemon().stop()
    emod.JobManager().stop()
    for t in threading.enumerate():
        if isinstance(t, StoppableThread):
            t.stop(timeout=timeout)

# numerical classes that are used everywhere
import numpy as np
import nidaqmx
from nidaqmx import *
from nidaqmx.constants import *
#########################################
# hardware
#########################################

#from hardware.dummy import Nidaq as nidaq

#########################################
# create measurements
#########################################
task_in = nidaqmx.Task()
task_out = nidaqmx.Task()
#task_lockin = nidaqmx.Task()

task_in.ai_channels.add_ai_voltage_chan("Dev3/ai0")
task_in.ai_channels.add_ai_voltage_chan("Dev3/ai1")
task_in.ai_channels.add_ai_voltage_chan("Dev3/ai2")
task_in.ai_channels.add_ai_voltage_chan("Dev3/ai3")
task_in.ai_channels.add_ai_voltage_chan("Dev3/ai4")
task_in.ai_channels.add_ai_voltage_chan("Dev3/ai5")
task_in.ai_channels.add_ai_voltage_chan("Dev3/ai6")
task_in.ai_term_cfg=TerminalConfiguration.RSE
#task_in.timing.cfg_samp_clk_timing(rate=1000)     #source of the sample clock, sample rate and the number of samples to acquire
task_in.ai_min = 0
task_in.ai_max = 0.3
#task_lockin.ai_channels.add_ai_voltage_chan("Dev1/ai1")


import measurements.magneto
magneto = measurements.magneto.Magneto(task_in)

#########################################
# fire up the GUI
#########################################


magneto.configure_traits()
