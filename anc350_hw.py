from ScopeFoundry import HardwareComponent
from ScopeFoundryHW.attocube_anc350.pyanc350v4 import PyANC350v4
import time
import threading


class AttocubeANC350StageHW(HardwareComponent):

    name = 'attocube_anc350'

    def __init__(self, app, debug=False, name=None, ax_names='xyz'):
        self.ax_names = ax_names
        HardwareComponent.__init__(self, app, debug=debug, name=name)
        


    def setup(self):

        self.add_operation("Meas_Cap", self.measure_capacitance)
        self.add_operation("Update_Status", self.update_status)
        self.add_operation("STOP_ALL", self.stop_all_movement)

        for axis_num, axis_name in [(0,self.ax_names[0]),(2,self.ax_names[1]),(1,self.ax_names[2])]: # y and z positioners are switched on the hardware side (they are x=0, z=1, y=2). Here we switch them back by adjusting the numbering
            # Skip axis if disable in __init__ ax_names
            if axis_name == '_':
                continue
            
            self.settings.New(axis_name + "_position", 
                               dtype=float,
                               ro=True,
                               unit='um',
                               spinbox_decimals=6,
                               si=False
                               )
            
            #self.settings.New(axis + "_ref_position", dtype=float, ro=True, unit='nm')
            
            self.settings.New(axis_name + "_target_position",
                                dtype=float,
                                ro=False,
                                vmin=0,
                                vmax=5000,
                                unit='um',
                                spinbox_decimals=6,
                                spinbox_step=0.1,
                                si=False)

            self.settings.New(axis_name + "_enable_output", dtype=bool, ro=False)
            self.settings.New(axis_name + "_enable_closedloop", dtype=bool,
                                                                 ro=False)
            # self.settings.New(axis + "_reference_found", dtype=bool,
            #                                                    ro=True)
            # self.settings.New(axis + "_reference_position", dtype=float,
            #                     spinbox_decimals=6, si = False,
            #                   unit='mm', ro=True)
                      
            #if self.pro:
            # self.settings.New(axis + "_auto_reference_update", dtype=bool,
            #                                                ro=False)
            # self.settings.New(axis + "_auto_reference_reset", dtype=bool,
            #                                                ro=False)
            # self.settings.New(axis + "_eot_stop", dtype=bool,
            #                                                ro=False)
            # done pro
       
            self.settings.New(axis_name + "_step_voltage",
                                dtype=float, vmin=0, vmax = 60, unit='V',
                                ro=False)
            #if self.pro:
            self.settings.New(axis_name + "_openloop_voltage", unit = 'V',
                                    dtype=float, si=False, ro=False)
        
        
            self.settings.New(axis_name + "_frequency", unit = 'Hz',
                                    dtype=float, vmin = 1, vmax = 10000, si=False, ro=False)

            self.settings.New(axis_name + "_capacitance", unit='F', si=True, ro=True)
            # done pro
                
            self.settings.New(axis_name + "_actor_type", dtype=str, ro=True)
            self.settings.New(axis_name + "_actor_name", dtype=str, ro=True)


            # Axis Status
            self.settings.New(axis_name + "_connected", dtype=bool, ro=True)
            self.settings.New(axis_name + "_is_enabled", dtype=bool, initial=True)
            self.settings.New(axis_name + "_moving", dtype=bool, initial=True)
            self.settings.New(axis_name + "_on_target", dtype=bool, ro=True)
            self.settings.New(axis_name + "_eot_forward", dtype=bool, ro=True)
            self.settings.New(axis_name + "_eot_back", dtype=bool, ro=True)
            self.settings.New(axis_name + "_error", dtype=bool, ro=True)

            self.settings.New(axis_name + "_jog_step", dtype=float,
                                    spinbox_decimals=6, si = False, unit='um', ro=False,
                                    initial=0.1)

            for sign in "pm":
                # Seems that pyqt passes a bool to func if func has arguments. ?
                # dump bool into *args and ignore
                func = lambda *args, axis_name=axis_name, sign=sign: self.move_jog_step(
                        axis_name=axis_name, sign=sign)     
                self.add_operation(axis_name + "_jog_"+sign, func)

                func2 = lambda *args, axis_num=axis_num, sign=sign: self.move_single_step(
                        axis_num=axis_num, sign=sign) 
                self.add_operation(axis_name + "_single_step_"+sign, func2)

                func3 = lambda *args, axis_num=axis_num, sign=sign: self.move_continuously(
                        axis_num=axis_num, start=1, sign=sign) 
                self.add_operation(axis_name + "_move_continuously_"+sign, func3)      

                    
    def connect(self):
        if self.settings['debug_mode']: print("connecting to attocube ANC350 {}".format(self.name))
        
        #self.settings.ip_address.change_readonly(True)

        self.anc = anc = PyANC350v4.Positioner()

        
        #self.amc.connect()
        
        #self.settings['pro_mode'] = self.amc.pro_version_check()
        
        for axis_num, axis_name in [(0,self.ax_names[0]),(2,self.ax_names[1]),(1,self.ax_names[2])]: # y and z positioners are switched on the hardware side (they are x=0, z=1, y=2). Here we switch them back by adjusting the numbering
            print(axis_num, axis_name)
            if axis_name != "_":
                # Enable Axes
                # ECC_controlOutput
                #self.amc.control.setControlOutput(axis_num,enable=True)
                
                self.anc.setTargetRange(axis_num,1) #this sets the range around the target position where the target is considered to be reached. Input is in um.
                # connect logged quantities
                
                self.settings.get_lq(axis_name + "_position").connect_to_hardware(
                    lambda a=axis_num: self.anc.getPosition(a))
                
                
        

                def move_to_target(a, new_pos): #the position is entered in um. conversion to SI units is done in the lower level functions.
                    self.anc.setTargetPosition(a, new_pos)
                    self.anc.startAutoMove(a, True, relative=False)

                self.settings.get_lq(axis_name + "_target_position").connect_to_hardware(
#                    read_func = lambda a=axis_num: self.amc.control.getControlTargetPosition(a)[1],
                    #write_func = lambda new_pos, a=axis_num: self.anc.setTargetPosition(a, new_pos))
                    write_func = lambda new_pos, a=axis_num: move_to_target(a, new_pos))
                
                self.settings.get_lq(axis_name + "_step_voltage").connect_to_hardware(
                    read_func = lambda a=axis_num: self.anc.getAmplitude(a),
                    write_func = lambda volts, a=axis_num: self.anc.setAmplitude(a,volts))
                    
                # self.settings.get_lq(axis_name + "_electrically_connected").connect_to_hardware(
                #     lambda a=axis_num: self.amc.status.getStatusConnected(a))
                
                # self.settings.get_lq(axis_name + "_reference_found").connect_to_hardware(
                #     lambda a=axis_num: self.amc.status.getStatusReference(a)[1])

                # self.settings.get_lq(axis_name + "_reference_position").connect_to_hardware(
                #     lambda a=axis_num: self.amc.control.getReferencePositionInmm(a)[1])
                
                self.settings.get_lq(axis_name + "_enable_output").connect_to_hardware(
                    #read_func  = lambda a=axis_num: self.anc.getAxisOutput(a),
                    write_func = lambda enable, a=axis_num: self.anc.setAxisOutput(a, enable, autoDisable=True))
                    
                self.settings.get_lq(axis_name + "_enable_closedloop").connect_to_hardware(
                    #read_func = lambda a=axis_num: self.amc.control.getControlMove(a)[1],
                    write_func = lambda enable, a=axis_num: self.anc.startAutoMove(a, enable, relative=False)
                    )
                
                #FIXME
                #                 self.settings.get_lq(axis_name + "_continuous_motion").connect_to_hardware(
                #                     read_func = lambda a=axis_num: self.ecc100.(a),
                #                     write_func = lambda dir, a=axis_num: self.ecc100.start_continuous_motion(a, dir)
                #                     )
                                    
                # Target Status is NCB_FeatureNotAvailable
                #self.settings.get_lq(axis_name + "_target_status").connect_to_hardware(
                #    read_func = lambda a=axis_num: self.ecc100.read_target_status(a) 
                #    )

                #if self.settings['pro_mode']:
                if True:
                    #                     self.x_openloop_voltage.hardware_read_func = lambda: self.ecc100.read_openloop_voltage(X_AXIS)
                    #                     self.x_openloop_voltage.hardware_set_func = lambda x: self.ecc100.write_openloop_voltage(X_AXIS, x)
                                    
                    # self.settings.get_lq(axis_name + "_eot_stop").connect_to_hardware(
                    #     read_func = lambda a=axis_num: self.amc.control.getControlEotOutputDeactive(a)[1],
                    #     write_func = lambda enable, a=axis_num: self.amc.control.setControlEotOutputDeactive(a,enable))
                    # self.settings.get_lq(axis_name + "_eot_forward").connect_to_hardware(
                    #     lambda a=axis_num: self.amc.status.getStatusEotFwd(a)[1])
                    # self.settings.get_lq(axis_name + "_eot_back").connect_to_hardware(
                    #     lambda a=axis_num: self.amc.status.getStatusEotBkwd(a)[1])
                    self.settings.get_lq(axis_name + "_frequency").connect_to_hardware(
                        read_func = lambda a=axis_num: self.anc.getFrequency(a),
                        write_func = lambda freq, a=axis_num: self.anc.setFrequency(a,freq))
                    # self.settings.get_lq(axis_name + "_auto_reference_update").connect_to_hardware(
                    #     read_func = lambda a=axis_num: self.amc.control.getControlReferenceAutoUpdate(a)[1],
                    #     write_func = lambda enable, a=axis_num: self.amc.control.setControlReferenceAutoUpdate(a,enable))
                    # self.settings.get_lq(axis_name + "_auto_reference_reset").connect_to_hardware(
                    #     read_func = lambda a=axis_num: self.amc.control.getControlAutoReset(a)[1],
                    #     write_func = lambda enable, a=axis_num: self.amc.control.setControlAutoReset(a,enable))
                        
                self.settings.get_lq(axis_name + "_actor_type").connect_to_hardware(
                    lambda a=axis_num: self.anc.getActuatorTypeName(a)) 
                self.settings.get_lq(axis_name + "_actor_name").connect_to_hardware(
                    lambda a=axis_num: self.anc.getActuatorName(a))

        self.measure_capacitance()
        self.read_from_hardware()

        for axis in self.ax_names:
            self.settings[axis + '_target_position']=self.settings[axis + '_position']

        # TODO
        #         # update units based on Actor type
        #         for axis_num, axis_name in enumerate(self.ax_names):
        #             if axis_name != "_":
        #                 actor_type = self.settings[axis_name + "_actor_type"]
        #                 if actor_type == 'ECC_actorLinear':
        #                     self.settings.get_lq(axis_name + "_position").change_unit("mm")
        #                     self.settings.get_lq(axis_name + "_target_position").change_unit("mm")
        #                 elif actor_type in ['ECC_actorGonio', 'ECC_actorRot']:
        #                     self.settings.get_lq(axis_name + "_position").change_unit("deg")
        #                     self.settings.get_lq(axis_name + "_target_position").change_unit("deg")
        #                     
        #         # find axes with step voltage too small due to weird firmware issues
        #         for axis_num, axis_name in enumerate(self.ax_names):
        #             if axis_name != "_":
        #                 step_volt = self.settings.get_lq(axis_name + "_step_voltage")
        #                 if step_volt.val < 5:
        #                     step_volt.update_value(30)
        #                 step_freq = self.settings.get_lq(axis_name + "_frequency")
        #                 if step_freq.val < 5:
        #                     step_freq.update_value(1000)
    
        #turn on the autorefresh
        self.update_thread_interrupted = False
        self.update_thread = threading.Thread(target=self.update_thread_run, daemon=True)        
        self.update_thread.start()

                    

    def disconnect(self):
        
        self.settings.disconnect_all_from_hardware()

        if hasattr(self, 'update_thread'):
            self.update_thread_interrupted = True
            self.update_thread.join()
            del self.update_thread
        
        if hasattr(self, 'anc'):
            self.anc.disconnect()
            
            del self.anc


    def measure_capacitance(self):
        for axis_num, axis_name in [(0,self.ax_names[0]),(2,self.ax_names[1]),(1,self.ax_names[2])]: # y and z positioners are switched on the hardware side (they are x=0, z=1, y=2). Here we switch them back by adjusting the numbering
            print("measure_capacitance", axis_num, axis_name)
            if axis_name == "_":
                continue
            self.settings[axis_name + "_capacitance"] = self.anc.measureCapacitance(axis_num)


    def update_status(self):
        S = self.settings
        for axis_num, axis_name in [(0,self.ax_names[0]),(2,self.ax_names[1]),(1,self.ax_names[2])]: # y and z positioners are switched on the hardware side (they are x=0, z=1, y=2). Here we switch them back by adjusting the numbering
            #print(axis_num, axis_name)
            if axis_name == "_":
                continue
            connected,enabled, moving, target, eotFwd, eotBwd, err = self.anc.getAxisStatus(axis_num)

            S[axis_name + '_connected'] = connected
            S[axis_name + '_is_enabled'] = enabled
            S[axis_name + '_moving'] = moving
            S[axis_name + '_on_target'] = target
            S[axis_name + '_eot_forward'] = eotFwd
            S[axis_name + '_eot_back'] = eotBwd
            S[axis_name + '_error'] = err
        
                
    def move_jog_step(self, axis_name, sign):
        S = self.settings
        delta = {"p": 1.0, "m": -1.0}[sign] * S[axis_name + "_jog_step"]
        S[axis_name + "_target_position"] += delta 

    def move_single_step(self,axis_num,sign):
        backward={"p": 0, "m": 1}[sign]
        self.anc.startSingleStep(axis_num,backward)

    def move_continuously(self,axis_num,start,sign):
        backward={"p": 0, "m": 1}[sign]
        self.anc.startContinuousMove(axis_num, start, backward)

    def stop_all_movement(self):
        self.anc.startContinuousMove(0, 0, 1)
        self.anc.startContinuousMove(2, 0, 1)
        self.anc.startContinuousMove(1, 0, 1)

    def update_thread_run(self):
        while not self.update_thread_interrupted:
            self.read_from_hardware()
            time.sleep(0.1)
