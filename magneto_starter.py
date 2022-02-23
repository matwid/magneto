"""EPR startup script"""
import os
import inspect
from traits.api         import HasTraits, Instance, SingletonHasTraits, Range, on_trait_change, Int
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
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx import constants

#########################################
# hardware
#########################################

#from hardware.dummy import Nidaq as nidaq

#########################################
# create measurements
#########################################

sampling_freq_in = 1000  # in Hz default= 1000
buffer_in_size = 100
bufsize_callback = buffer_in_size
buffer_in_size_cfg = round(buffer_in_size * 1)  # clock configuration
chans_in =3

# Initialize data placeholders
buffer_in = np.zeros((chans_in, buffer_in_size))
data = np.zeros((chans_in, 3))  # will contain a first column with zeros but that's fine

# uses above parameters
# added channels have to match with chans_in
def cfg_read_task(acquisition):  
    acquisition.ai_channels.add_ai_voltage_chan("Dev3/ai0", max_val=2.5, min_val=0)  
    acquisition.ai_channels.add_ai_voltage_chan("Dev3/ai1", max_val=10, min_val=0)
    acquisition.ai_channels.add_ai_voltage_chan("Dev3/ai2", max_val=10, min_val=0)
    acquisition.timing.cfg_samp_clk_timing(rate=sampling_freq_in, sample_mode=constants.AcquisitionType.CONTINUOUS,
                                           samps_per_chan=buffer_in_size_cfg)
    
def reading_task_callback(task_idx, event_type, num_samples, callback_data):  # bufsize_callback is passed to num_samples
    global data
    global buffer_in

    # It may be wiser to read slightly more than num_samples here, to make sure one does not miss any sample,
    # see: https://documentation.help/NI-DAQmx-Key-Concepts/contCAcqGen.html
    buffer_in = np.zeros((chans_in, num_samples)) 
    stream_in.read_many_sample(buffer_in, num_samples, timeout=constants.WAIT_INFINITELY)
    data = np.append(data, buffer_in, axis=1) 

    return 0  # Absolutely needed for this callback to be well defined (see nidaqmx doc).


task_in = nidaqmx.Task()
cfg_read_task(task_in)
stream_in = AnalogMultiChannelReader(task_in.in_stream)
task_in.register_every_n_samples_acquired_into_buffer_event(bufsize_callback, reading_task_callback)
import measurements.magneto
magneto = measurements.magneto.Magneto(task_in, sampling_freq_in)

#########################################
# fire up the GUI
#########################################
magneto.configure_traits()
