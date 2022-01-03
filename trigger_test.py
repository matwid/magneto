import numpy as np
import nidaqmx
from nidaqmx import *
from nidaqmx.constants import *

task_ai = nidaqmx.Task()

task_ai.ai_channels.add_ai_voltage_chan("Dev3/ai1", max_val=10, min_val=0)
task_ai.ai_channels.add_ai_voltage_chan("Dev3/ai2", max_val=10, min_val=0)
#trig_task.triggers.reference_trigger.cfg_anlg_edge_ref_trig("Dev3/ai4", pretrigger_samples = 10, trigger_slope=nidaqmx.constants.Slope.RISING, trigger_level = 1.61)
task_ai.triggers.start_trigger.cfg_anlg_edge_start_trig(trigger_source="APFI0", trigger_slope=nidaqmx.constants.Slope.RISING, trigger_level=0.5)
#task_in.ai_term_cfg=TerminalConfiguration.RSE

def reading_task_callback(task_idx, event_type, num_samples, callback_data):  # bufsize_callback is passed to num_samples
    global data
    global buffer_in

    if running:
        # It may be wiser to read slightly more than num_samples here, to make sure one does not miss any sample,
        # see: https://documentation.help/NI-DAQmx-Key-Concepts/contCAcqGen.html
        buffer_in = np.zeros((chans_in, num_samples))  # double definition ???
        stream_in.read_many_sample(buffer_in, num_samples, timeout=constants.WAIT_INFINITELY)

        data = np.append(data, buffer_in, axis=1)  # appends buffered data to total variable data

    return 0  # Absolutely needed for this callback to be well defined (see nidaqmx doc).



task_ai.start()

task_ai.stop()
task_ai.close()
