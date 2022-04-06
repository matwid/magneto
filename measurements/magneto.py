import numpy as np


from tools.chaco_addons import SavePlot as Plot, SaveTool

from traits.api       import SingletonHasTraits, Instance, Range, Bool, Array, Str, Enum, Button, on_trait_change, Trait, Float, Int
from traitsui.api     import View, Item, Group, HGroup, VGroup, VSplit, Tabbed, EnumEditor
from enable.api       import ComponentEditor, Component
from chaco.api        import PlotAxis, CMapImagePlot, ColorBar, LinearMapper, ArrayPlotData, Spectral
import logging

from tools.emod import FreeJob
from tools.utility import GetSetItemsMixin, timestamp
import time


import threading



class Magneto( FreeJob, GetSetItemsMixin ):
    """
    Measures OPM data.

      last modified
    """
      


    x_axis           = Enum('Time')
    #trigger_channel  = Enum('Channel 0','Channel 1', 'Channel 2')
    #trigger_level    = Float(default_value=1.3)
    y_axis           = Enum('Trigger Channel', 'Channel 0', 'Channel 1', 'Channel 2')

      

    v_divisions       = Range(low=0, high=1e6,       value=100,     desc='divisions [#]',  label='divisions [#]',   mode='text', auto_set=False, enter_set=True)
    v_reset           = Float(default_value=0, label='reset voltage')

    samples_per_channel = Int(default_value=1000, desc='Samples per channel', label='Samples per channel', mode='text', auto_set=False, enter_set=True)
    proceed             = Float(default_value=0.0, label='proceed [%]')
 

    scale             = Enum('lin','log',value='log', desc='scale')
    plot_tpe          = Enum('line', 'scatter')

    use_trigger       = Bool(False)
    append_data        = Bool(False)
    wait_between_trigger = Float(default_value=0.5, label='wait time between trigger')


    time_data         = Array()
    analog_in_trigger = Array()
    analog_in_0       = Array()
    analog_in_1       = Array()
    analog_in_2       = Array()

    time_data_stack   = Array()
    analog_in_0_stack = Array()
    analog_in_1_stack = Array()
    analog_in_2_stack = Array()

    x_data_plot       = Array()#for ploting
    y_data_plot       = Array()#
    x_data_plot_fft   = Array()#for ploting
    y_data_plot_fft   = Array()#

    plot_data         = Instance( ArrayPlotData )
    plot              = Instance( Plot )
    plot_data_fft     = Instance( ArrayPlotData )
    plot_fft          = Instance( Plot )

    bias_button = Button(label='set bias', show_label=False)
    bias_measured_button =  Button(label='measuerd bias', show_label=False)
    bias_value = Float()


    max_current = Float(default_value=10e-3, label='max current')

    get_set_items=['__doc__', 'time_data', 'time_data_stack', 'samples_per_channel', 'analog_in_trigger', 'analog_in_0', 'analog_in_1', 'analog_in_2', 'analog_in_0_stack', 'analog_in_1_stack', ]

    traits_view = View(VGroup(HGroup(Item('start_button',   show_label=False),
                                     Item('stop_button',   show_label=False),
                                     Item('state',       style='readonly'),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),

                              HGroup(Item('samples_per_channel'),
                                     #Item('use_trigger'),
                                     #Item('trigger_level'),
                                     Item('append_data'),
                                     #Item('wait_between_trigger'),

                                     Item('plot_tpe')
                                     ),
                              HGroup(
                                     Item('x_axis'),
                                     Item('y_axis')
                                     ),                                     
                              Item('plot', editor=ComponentEditor(), show_label=False, resizable=True),
                              Item('plot_fft', editor=ComponentEditor(), show_label=False, resizable=True),

                              ),
                       title='Magneto Software for OPM recording', buttons=[], resizable=True
                    )

    def __init__(self, task_in, sampling_freq_in, **kwargs):
        super(Magneto, self).__init__(**kwargs)

        self._create_plot()
        self._create_plot_fft()
        self.task_in = task_in
        self.sampling_freq_in = sampling_freq_in

        
        self.on_trait_change(self._update_index,    'x_data_plot',    dispatch='ui')
        self.on_trait_change(self._update_value,    'y_data_plot',    dispatch='ui') 
        self.on_trait_change(self._update_index_fft,    'x_data_plot_fft',    dispatch='ui')
        self.on_trait_change(self._update_value_fft,    'y_data_plot_fft',    dispatch='ui') 

    def skip_first_data(self):
        # because of some weird data
        self.task_in.read(number_of_samples_per_channel=100)
        #self.trig_in.read(number_of_samples_per_channel=100)


    def _run(self):

        self.measurment_stopped = 'false'
        self.task_in.start()
        
        try:
            self.state='wait'
            self.time_data = np.array(())
            self.analog_in_trigger = np.array(())
            self.analog_in_0 = np.array(())
            self.analog_in_1 = np.array(())
            self.analog_in_2 = np.array(())
            temp=np.array(())

            #intial_d_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel)

            initial_array=np.zeros(self.samples_per_channel) 
                  
            
            self.analog_in_trigger = initial_array
            self.analog_in_0 = initial_array
            self.analog_in_1 = initial_array
            self.analog_in_2 = initial_array
            self.analog_in_0_stack = initial_array
            self.analog_in_1_stack = initial_array
            
            time_data=np.arange(0,self.samples_per_channel,1)
            self.skip_first_data()
            self.state='run'
            self.time_data = time_data

            while True: 
                self.measurment_finished = 'false' # Stop button only works while loop is active 

                if self.thread.stop_request.isSet():
                    logging.getLogger().debug('Caught stop signal. Exiting.')
                    self.state = 'idle'
                    break
                
                # Actual Measurement
                measured_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel) 
                self.analog_in_trigger=measured_data[0]
                self.analog_in_0=measured_data[1]
                self.analog_in_1=measured_data[2]
                self.analog_in_2=measured_data[3]
                #self.acquire_data(measured_data)
                    
                self.x_data_fft = np.fft.rfftfreq(self.samples_per_channel,d=1/self.sampling_freq_in)
                self.y_data_fft_trigger = np.abs(np.fft.rfft(self.analog_in_trigger))
                self.y_data_fft_0 = np.abs(np.fft.rfft(self.analog_in_0))
                self.y_data_fft_1 = np.abs(np.fft.rfft(self.analog_in_1))
                self.y_data_fft_2 = np.abs(np.fft.rfft(self.analog_in_2))

                self.plot_data_on_x()
                self.plot_data_on_y()

                self.plot_fft_x()
                self.plot_fft_y()
                
                """
                # triggerd and not stacked
                if self.use_trigger and not self.append_data:
                    if self.task_in.read()[0] > self.trigger_level:
                        measured_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel)
                        analog_in_1 = measured_data[1]
                        self.acquire_data(measured_data)
                        
                        self.x_data_plot_fft = time_data
                        self.y_data_plot_fft = self.analog_in_1
                        self.plot_data_on_x()
                        self.plot_data_on_y()
                        
                        time.sleep(self.wait_between_trigger)

                # triggerd and stacked
                if self.use_trigger and self.append_data:
                    if self.task_in.read()[0] > self.trigger_level:
                        
                        measured_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel)
                        analog_in_1 = measured_data[1]
                        self.acquire_data(measured_data)
                        
                        self.x_data_plot_fft = self.time_data_stack
                        self.y_data_plot_fft = self.analog_in_1_stack
                        self.plot_data_on_x_stack()
                        self.plot_data_on_y_stack()
                        
                        time.sleep(self.wait_between_trigger)


                # not triggerd and not stacked
                if not self.use_trigger and not self.append_data:
                   
                    measured_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel) 
                    analog_in_1=measured_data[1]
                    self.acquire_data(measured_data)
                    
                    self.x_data_plot_fft = np.fft.rfftfreq(self.samples_per_channel,d=1/self.sampling_freq_in)
                    self.y_data_plot_fft = np.abs(np.fft.rfft(self.analog_in_0))

                    self.x_data_plot_fft_Ch1 = np.fft.rfftfreq(self.samples_per_channel,d=1/self.sampling_freq_in)
                    self.y_data_plot_fft_Ch1 = np.abs(np.fft.rfft(self.analog_in_1))

                    self.x_data_plot_fft_Ch2 = np.fft.rfftfreq(self.samples_per_channel,d=1/self.sampling_freq_in)
                    self.y_data_plot_fft_Ch2 = np.abs(np.fft.rfft(self.analog_in_2))

                    self.plot_data_on_x()
                    self.plot_data_on_y()  
                

                # not triggerd and stacked
                if not self.use_trigger and self.append_data:
                    
                    measured_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel)
                    analog_in_1 = measured_data[1]
                    self.acquire_data(measured_data)
                    

                    # self.x_data_plot_fft = np.fft.rfftfreq(len(self.analog_in_0_stack),d=1/1000)
                    # self.y_data_plot_fft = np.abs(np.fft.rfft(self.analog_in_0_stack))

                    # self.x_data_plot_fft_Ch1 = np.fft.rfftfreq(len(self.analog_in_1_stack),d=1/1000)
                    # self.y_data_plot_fft_Ch1 = np.abs(np.fft.rfft(self.analog_in_1_stack))

                    # self.x_data_plot_fft_Ch2 = np.fft.rfftfreq(len(self.analog_in_2_stack),d=1/1000)
                    # self.y_data_plot_fft_Ch2 = np.abs(np.fft.rfft(self.analog_in_2_stack))

                    self.plot_data_on_x_stack()
                    self.plot_data_on_y_stack()
                    """

            else:
                self.state='done'


        except:
            logging.getLogger().exception('Error in measurement.')
            self.task_in.stop()
            self.state = 'error'

        finally:
            self.measurment_finished = 'true'
            self.task_in.stop()
            self.state = 'done'

    #################################################################
    # Helper Methods
    #################################################################

    

    def _bias_measured_button_fired(self):
        measured_data = self.task_in.read()
        self.bias_value = measured_data[0]

    """
    def acquire_data(self,measured_data):
        analog_in_0 = measured_data[0]
        analog_in_1 = measured_data[1]
        analog_in_2 = measured_data[2]

        #self.analog_in_0 = self.analog_in_0+analog_in_0
        #self.analog_in_1 = self.analog_in_1+analog_in_1
        #self.analog_in_2 = self.analog_in_2+analog_in_2

        self.analog_in_0 = analog_in_0
        self.analog_in_1 = analog_in_1
        self.analog_in_2 = analog_in_2

        self.analog_in_0_stack = np.append(self.analog_in_0_stack,analog_in_0)
        self.analog_in_1_stack = np.append(self.analog_in_1_stack,analog_in_1)
        self.analog_in_2_stack = np.append(self.analog_in_2_stack,analog_in_2)
        self.time_data_stack   = np.arange(0, len(self.analog_in_1_stack))
        return 
    """     

    #################################################################
    # PLOT DEFINITIONS
    #################################################################

    def _create_plot(self):
        plot_data = ArrayPlotData(x_data_plot=np.array(()), y_data_plot=np.array(()))
        plot = Plot(plot_data, padding=8, padding_left=64, padding_bottom=64)
        plot.plot(('x_data_plot','y_data_plot'), color='blue', type='line')
        plot.value_axis.title = 'Voltage [V]'
        plot.index_axis.title = 'Time (arb. u.)'
        plot.tools.append(SaveTool(plot))
        self.plot_data = plot_data
        self.plot = plot

    def _create_plot_fft(self):
        plot_data = ArrayPlotData(x_data_plot_fft=np.array(()), y_data_plot_fft=np.array(()))
        plot = Plot(plot_data, padding=8, padding_left=64, padding_bottom=64)
        plot.plot(('x_data_plot_fft','y_data_plot_fft'), color='blue', type='line',value_scale='log')
        plot.value_axis.title = 'Amplitude'
        plot.index_axis.title = 'Frequency [Hz]'
        plot.tools.append(SaveTool(plot))
        self.plot_data_fft = plot_data
        self.plot_fft = plot        
        
    @on_trait_change('x_axis')
    def _update_naming_x(self): 
        if self.x_axis == 'Time':
            self.plot.index_axis.title = 'Time (arb. u.)'
            self.x_data_plot = self.time_data
            return

           
    @on_trait_change('y_axis')
    def _update_naming_y(self):   
        if self.y_axis == 'Trigger Channel':
            self.plot.value_axis.title ='Trigger Channel [V]'
            self.y_data_plot = self.analog_in_trigger
            return
        if self.y_axis == 'Channel 0':
            self.plot.value_axis.title ='Channel 0 [V]'
            self.y_data_plot = self.analog_in_0
            return
        elif self.y_axis == 'Channel 1':
            self.plot.value_axis.title = 'Channel 1 [V]'
            self.y_data_plot = self.analog_in_1
            return
        elif self.y_axis == 'Channel 2':
            self.plot.value_axis.title = 'Channel 2 [V]'
            self.y_data_plot =  self.analog_in_2
            return 


    def _update_index(self, new):
        self.plot_data_on_x()
        self.plot_data.set_data('x_data_plot', new)
 
    def _update_value(self, new):
        self.plot_data_on_y()
        self.plot_data.set_data('y_data_plot', new)
      
    def _update_index_fft(self, new):
        self.plot_fft_x()
        self.plot_data_fft.set_data('x_data_plot_fft', new)

    def _update_value_fft(self, new):
        self.plot_fft_y()
        self.plot_data_fft.set_data('y_data_plot_fft', new)
    
    
    def save_plot(self, filename):
        self.save_figure(self.plot, filename)

    def save_all(self, filename):
        self.save(filename+'.pys')
        self.save(filename+'-ACSII.pys')
        np.savetxt(filename+'.txt',(self.voltage,self.login_V_data))
    

    # plot single measurement
    def plot_data_on_x(self):
        if self.x_axis == 'Time':
            self.x_data_plot = self.time_data
            return

    def plot_data_on_y(self):    
        if self.y_axis == 'Trigger Channel':
            self.y_data_plot = self.analog_in_trigger
            return
        if self.y_axis == 'Channel 0':
            self.y_data_plot = self.analog_in_0
            return
        elif self.y_axis == 'Channel 1':
            self.y_data_plot = self.analog_in_1
            return
        elif self.y_axis == 'Channel 2':
            self.y_data_plot =  self.analog_in_2
            return

    def plot_fft_x(self):
        if self.x_axis == 'Time':
            self.x_data_plot_fft = self.x_data_fft
            return

    def plot_fft_y(self):
        if self.y_axis == 'Trigger Channel':
            self.y_data_plot_fft = self.y_data_fft_trigger
            return
        if self.y_axis == 'Channel 0':
            self.y_data_plot_fft = self.y_data_fft_0
            return
        elif self.y_axis == 'Channel 1':
            self.y_data_plot_fft = self.y_data_fft_1
            return
        elif self.y_axis == 'Channel 2':
            self.y_data_plot_fft =  self.y_data_fft_2
            return

    # plot the continuously stacked data
    def plot_data_on_x_stack(self):
        if self.x_axis == 'Time':
            self.x_data_plot = self.time_data_stack[0:(len(self.time_data_stack)-self.samples_per_channel)]
            return
        elif self.x_axis == 'Channel 0':
            self.x_data_plot = self.analog_in_0_stack[self.samples_per_channel:len(self.analog_in_0_stack)]
            return
        elif self.x_axis == 'Channel 1':
            self.x_data_plot =  self.analog_in_1_stack[self.samples_per_channel:len(self.analog_in_1_stack)]
            return
        elif self.x_axis == 'Channel 2':
            self.x_data_plot =  self.analog_in_2_stack[self.samples_per_channel:len(self.analog_in_2_stack)]
            return       
    
    def plot_data_on_y_stack(self):    
        if self.y_axis == 'Channel 0':
            self.y_data_plot = self.analog_in_0_stack[self.samples_per_channel:len(self.analog_in_0_stack)]
            return
        elif self.y_axis == 'Channel 1':
            self.y_data_plot = self.analog_in_1_stack[self.samples_per_channel:len(self.analog_in_1_stack)]
            return
        elif self.y_axis == 'Channel 2':
            self.y_data_plot =  self.analog_in_2_stack[self.samples_per_channel:len(self.analog_in_2_stack)]
            return
        elif self.y_axis == 'Time':
            self.y_data_plot =  self.time_data_stack
            return
    
              

if __name__=='__main__':
    magneto = Magneto()
    magneto.configure_traits()
