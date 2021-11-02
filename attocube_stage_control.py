from ScopeFoundry import Measurement
import time
from qtpy import  QtWidgets
from PyQt5.Qt import QFormLayout,QVBoxLayout
from boto.sdb.db.sequence import double
import numpy as np
from builtins import getattr

class AttoCubeANC350StageControlMeasure(Measurement):
    
    name = 'attocube_stage_control_ANC350'
    
    def __init__(self, app, name=None, hw_name='attocube_anc350'):
        self.hw_name = hw_name
        Measurement.__init__(self, app, name=name)
    
    def setup(self):
        
        self.hw = self.app.hardware[self.hw_name]
        self.S = S = self.hw.settings
                
        self.ui = QtWidgets.QWidget()
        self.ui.setLayout(QtWidgets.QVBoxLayout())
        self.ctr_box = QtWidgets.QGroupBox("Attocube ANC350: {} {}".format(self.name, self.hw_name))
        self.ctr_box.setLayout(QtWidgets.QHBoxLayout())
        self.ui.layout().addWidget(self.ctr_box, stretch=0)

        self.connect_checkBox = QtWidgets.QCheckBox("Connect to Hardware") 
        self.ctr_box.layout().addWidget(self.connect_checkBox)
        S.connected.connect_to_widget(self.connect_checkBox)
        
        self.run_checkBox = QtWidgets.QCheckBox("Live Update")
        self.ctr_box.layout().addWidget(self.run_checkBox)
        self.settings.activation.connect_to_widget(self.run_checkBox)
        
        # self.dev_id_doubleSpinBox = QtWidgets.QDoubleSpinBox()
        # self.ctr_box.layout().addWidget(self.dev_id_doubleSpinBox)
        # S.device_id.connect_to_widget(self.dev_id_doubleSpinBox)


        self.axes_box = QtWidgets.QGroupBox("Axes")
        self.axes_box.setLayout(QtWidgets.QHBoxLayout())
        self.ui.layout().addWidget(self.axes_box, stretch=0)
        for i,axis in enumerate(self.hw.ax_names):
            names = [name for name in S.as_dict().keys() if name.split('_')[0] == axis]
            widget = S.New_UI(names)
            widget.layout().insertRow(0, "Axis {}".format(i+1), QtWidgets.QLabel("<B>{}</B>".format(axis)))
            self.axes_box.layout().addWidget(widget)
        
        self.jog_box = QtWidgets.QGroupBox("Jog")
        self.jog_box.setLayout(QtWidgets.QHBoxLayout())
        self.ui.layout().addWidget(self.jog_box, stretch=0)        
        for i,axis in enumerate(self.hw.ax_names):
            
            ui_widget =  QtWidgets.QWidget()
            formLayout = QtWidgets.QVBoxLayout()
            ui_widget.setLayout(formLayout)
    
            doubleSpinBox = QtWidgets.QDoubleSpinBox()            
            jog_step_lq = getattr(self.S,axis + "_jog_step")
            jog_step_lq.connect_to_widget(doubleSpinBox)
            formLayout.addWidget(doubleSpinBox)            
            for sign in "pm":
                func = self.hw.operations[axis + "_jog_"+sign]
                pushButton = QtWidgets.QPushButton({"p":"+", "m":"-"}[sign])
                pushButton.clicked.connect(func)
                formLayout.addWidget(pushButton)
            
            self.jog_box.layout().addWidget(ui_widget, stretch=0)
                        
        self.ui.layout().addWidget(self.jog_box, stretch=0)      
        

        self.settings.New(name='wobble', dtype=bool, initial=False, ro=False)
        self.settings.New(name='wobble_axis', dtype=str, initial ='z', ro=False)
        self.settings.New(name='wobble_amplitude',  dtype=float, initial=0.015, unit = 'mm', ro=False, spinbox_decimals=3)
        self.settings.New(name='wobble_period', dtype=float, initial=1, unit='s', ro=False)

              
        self.ui.layout().addWidget(QtWidgets.QWidget(), stretch=1)
    
    def setup_figure(self):
        pass
    
    def run(self):
        wobble_counter = 0
        
        while not self.interrupt_measurement_called:
            time.sleep(0.1)
            self.hw.read_from_hardware()
            self.hw.update_status()
            #print("read")
            
            # if self.settings['wobble']:
            #     self.wobble()
            #     wobble_counter += 1
            # if wobble_counter == 1000: #stop
            #     self.settings['wobble'] = False  
            # pass
    
    def wobble(self):
        z_0 = self.S['{}_position'.format(self.settings['wobble_axis'])] #initial position
        A_z = self.settings['wobble_amplitude']
        t_period = self.settings['wobble_period']
        
        dt = 0.05
        steps = int(np.ceil(t_period/dt))
        for n in np.arange(1,steps+1,1):
            delta_z = A_z*np.sin(n/steps*2*np.pi)
            self.move_to_z_position(z_0+delta_z, dt)
        
        #make sure its back to initial position, take a break
        self.move_to_z_position(z_0, 0.2)
    

    def move_to_z_position(self, z_target_position, t_wait):
        self.S['z_target_position'] = z_target_position
        time.sleep(t_wait)

        
        
    def update_display(self):
        pass
    
    

