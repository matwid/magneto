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
    """
    #Test setting for time saving reasons ###################################################################################################################
    v_begin           = Range(low=0., high=10.,    value=0,    desc='begin [V]',  label='begin [V]',   mode='text', auto_set=False, enter_set=True)
    v_end             = Range(low=0.001, high=10.,    value=1,      desc='end [V]',    label='end [V]',     mode='text', auto_set=False, enter_set=True)
    v_bias            = Float(default_value=0,label=' ')
    v_delta           = Range(low=0., high=10.,       value=.1,     desc='delta [V]',  label='delta [V]',   mode='text', auto_set=False, enter_set=True)
    
    x_axis           = Enum('control voltage','hall voltage','logIn voltage')
    y_axis           = Enum('logIn voltage','control voltage', 'hall voltage')
    #################################################################################################################################################
    """

    


    x_axis           = Enum('Time', 'Channel 0','Channel 1', 'Channel 2')
    trigger_channel  = Enum('Channel 0','Channel 1', 'Channel 2')
    trigger_level   = Float(default_value=2.0)
    y_axis           = Enum('Channel 1', 'Channel 0','Channel 2', 'Time')

      

    v_divisions       = Range(low=0, high=1e6,       value=100,     desc='divisions [#]',  label='divisions [#]',   mode='text', auto_set=False, enter_set=True)
    v_reset           = Float(default_value=0, label='reset voltage')

    samples_per_channel = Int(default_value=20, desc='samples_per_channel', label='samples_per_channel', mode='text', auto_set=False, enter_set=True)
    proceed           = Float(default_value=0.0, label='proceed [%]')
 

    scale             = Enum('lin','log',value='log', desc='scale')
    plot_tpe          = Enum('line', 'scatter')

    use_trigger       = Bool(True)


    time_data         = Array()
    analog_in_0       = Array()
    analog_in_1       = Array()
    analog_in_2       = Array()
    analog_in_3       = Array()  
    analog_in_4       = Array()
    analog_in_5       = Array()
    analog_in_6       = Array()

    analog_in_0_stack = Array()
    analog_in_1_stack = Array()

    x_data_plot       = Array()#for ploting
    y_data_plot       = Array()#

    plot_data         = Instance( ArrayPlotData )
    plot              = Instance( Plot )

    bias_button = Button(label='set bias', show_label=False)
    bias_measured_button =  Button(label='measuerd bias', show_label=False)
    bias_value = Float()


    max_current = Float(default_value=10e-3, label='max current')

    get_set_items=['__doc__', 'time_data', 'samples_per_channel', 'analog_in_0', 'analog_in_1', 'analog_in_2', 'analog_in_3', 'analog_in_4', 'analog_in_5', 'analog_in_6' ]

    traits_view = View(VGroup(HGroup(Item('start_button',   show_label=False),
                                     Item('stop_button',   show_label=False),
                                     Item('state',       style='readonly'),
                                     Item('save_button', show_label=False),
                                     Item('load_button', show_label=False)
                                     ),

                              HGroup(Item('samples_per_channel'),
                                     Item('use_trigger'),
                                     Item('trigger_level'),

                                     Item('plot_tpe')
                                     ),
                              HGroup(
                                     Item('x_axis'),
                                     Item('y_axis')
                                     ),                                     
                              Item('plot', editor=ComponentEditor(), show_label=False, resizable=True),

                              ),
                       title='Magneto Software for OPM recording', buttons=[], resizable=True
                    )

    def __init__(self, task_in,  **kwargs):
        super(Magneto, self).__init__(**kwargs)

        self._create_plot()
        self.task_in = task_in

        
        self.on_trait_change(self._update_index,    'x_data_plot',    dispatch='ui')
        self.on_trait_change(self._update_value,    'y_data_plot',    dispatch='ui') 

    def skip_first_data(self):
        i=0
        while i< 50:
            self.task_in.read(number_of_samples_per_channel=1)
            i=i+1

    def _run(self):

        self.measurment_stopped = 'false'
        self.task_in.start()

        #self.trig_task.start()
        
        try:
            self.state='run'
            self.time_data = np.array(())
            self.analog_in_0 = np.array(())
            self.analog_in_1 = np.array(())
            self.analog_in_2 = np.array(())
            self.analog_in_3 = np.array(())
            self.analog_in_4 = np.array(())
            self.analog_in_5 = np.array(())
            self.analog_in_6 = np.array(())
            intial_d_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel)
            intital_trig_data = self.task_in.read(2)[0]
            #print('HERE', intial_d_data[0])
            initial_array=np.zeros(len(intial_d_data[0]))
            initial_trig_array=np.zeros(1)
            self.analog_in_0_stack = initial_array
            self.analog_in_1_stack = initial_array
            self.analog_in_0 = initial_array
            self.analog_in_1 = initial_array
            mytime = 0
            fake_time_data=np.arange(0,len(intial_d_data[0]),1)
            self.skip_first_data()
            while True: 
                self.measurment_finished = 'false' # Stop button only works while loop is active 

                #stop routine
                #self.thread.stop_request.wait(1)
                if self.thread.stop_request.isSet():
                    logging.getLogger().debug('Caught stop signal. Exiting.')
                    self.state = 'idle'
                    break

                
                #self.analog_in_0_stack=np.zeros(len(self.task_in.read(number_of_samples_per_channel=self.samples_per_channel))[0])

                if self.use_trigger:
                    if np.mean(self.task_in.read(2)[0]) > self.trigger_level:
                        measured_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel)
                        analog_in_0 = measured_data[0]
                        analog_in_1 = measured_data[1]
                        self.analog_in_0_stack = np.vstack((self.analog_in_0_stack, analog_in_0))
                        self.analog_in_1_stack = np.vstack((self.analog_in_1_stack, analog_in_1))
                        self.analog_in_0          = self.analog_in_0+analog_in_0
                        self.analog_in_1          = self.analog_in_1+analog_in_1 
                        self.time_data            = fake_time_data
                        self.plot_data_on_x()
                        self.plot_data_on_y()                     
                if not self.use_trigger:
                    mytime=mytime+1
                    measured_data = self.task_in.read(number_of_samples_per_channel=self.samples_per_channel)
                    analog_in_0 = np.mean(measured_data[0])
                    analog_in_1 = np.mean(measured_data[1])  
                    self.analog_in_0          = np.append(self.analog_in_0,     analog_in_0)
                    self.analog_in_1          = np.append(self.analog_in_1,     analog_in_1)
                    self.time_data            = np.append(self.time_data,       mytime) 
                    self.plot_data_on_x()
                    self.plot_data_on_y()  
                #AWG CH2 -> Clock, 100 Khz clock. BNC 2110 -> Trigger Counter PFI0/P10

                #analog_in_2 = np.mean(measured_data[2])
                #analog_in_3 = np.mean(measured_data[3])
                #analog_in_4 = np.mean(measured_data[4])
                #analog_in_5 = np.mean(measured_data[5])
                #analog_in_6 = np.mean(measured_data[6])
                

                # fills the storage arrays with the measured data 
                
                
                #self.analog_in_2          = np.append(self.analog_in_2,     analog_in_2)
                #self.analog_in_3          = np.append(self.analog_in_3,     analog_in_3)
                #self.analog_in_4          = np.append(self.analog_in_4,     analog_in_4)
                #self.analog_in_5          = np.append(self.analog_in_5,     analog_in_5)
                #self.analog_in_6          = np.append(self.analog_in_6,     analog_in_6)
               

                # writes the chosen data into the plot arrays


                
            else:

                self.state='done'


        except:
            logging.getLogger().exception('Error in measurement.')
            self.task_in.stop()

            self.state = 'error'

        finally:
            self.measurment_finished = 'true'
            self.task_in.stop()
            #self.task_in.close()

            self.state = 'done'

    #################################################################
    # Helper Methods
    #################################################################

    


    def _bias_measured_button_fired(self):
        measured_data = self.task_in.read()
        self.bias_value = measured_data[0]
     


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
        
        
    @on_trait_change('x_axis')
    def _update_naming_x(self): 
        if self.x_axis == 'Time':
            self.plot.index_axis.title = 'Time (arb. u.)'
            self.x_data_plot = self.time_data
            return
        elif self.x_axis == 'Channel 0':
            self.plot.index_axis.title = 'Channel 0 [V]'
            self.x_data_plot = self.analog_in_0
            return
        elif self.x_axis == 'Channel 1':
            self.plot.index_axis.title = 'Channel 1 [V]'
            self.x_data_plot = self.analog_in_1
            return
        elif self.x_axis == 'Channel 2':
            self.plot.index_axis.title = 'Channel 2 [V]'
            self.x_data_plot = self.analog_in_2
        elif self.x_axis == 'Channel 3':
            self.plot.index_axis.title = 'Channel 3 [V]'
            self.x_data_plot = self.analog_in_3
            return
           
    @on_trait_change('y_axis')
    def _update_naming_y(self):   
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
        elif self.y_axis == 'Time':
            self.plot.value_axis.title = 'Time arb. u.'
            self.y_data_plot =  self.time_data
            return     


    def _update_index(self, new):
        
        self.plot_data_on_x()
        self.plot_data.set_data('x_data_plot', new)


    def _update_value(self, new):
        self.plot_data_on_y()
        self.plot_data.set_data('y_data_plot', new)
   
    
    def save_plot(self, filename):
        save_figure(self.plot, filename)


    def save_all(self, filename):
        self.save(filename+'.pys')
        self.save(filename+'-ACSII.pys')
        self.np.savetxt(filename+'.txt',(self.voltage,self.login_V_data))
    

    def generate_voltage(self):
        if self.scale == 'lin':
            mesh = np.arange(self.v_begin, self.v_end, self.v_delta)
            return mesh
        if self.scale == 'log':
            difference = self.v_end-self.v_begin
            temp_mesh = np.logspace(0, np.log10(np.abs(difference)), self.v_divisions, base=10.0)
            mesh = temp_mesh - np.abs(difference)
            return mesh


    def plot_data_on_x(self):
        if self.x_axis == 'Time':
            self.x_data_plot = self.time_data
            return
        elif self.x_axis == 'Channel 1':
            self.x_data_plot = self.analog_in_1
            return
        elif self.x_axis == 'Channel 2':
            self.x_data_plot =  self.analog_in_2
            return
        elif self.x_axis == 'Channel 3':
            self.x_data_plot =  self.analog_in_3
            return            
            

    def plot_data_on_y(self):    
        if self.y_axis == 'Channel 1':
            self.y_data_plot = self.analog_in_1
            return
        elif self.y_axis == 'Channel 2':
            self.y_data_plot = self.analog_in_2
            return
        elif self.y_axis == 'Channel 3':
            self.y_data_plot =  self.analog_in_3
            return
        elif self.y_axis == 'Time':
            self.y_data_plot =  self.time_data
            return

if __name__=='__main__':
    magneto = Magneto()
    magneto.configure_traits()
