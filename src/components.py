from tkinter import Tk, ttk, RIGHT, LEFT, E, N, Menu
import tkinter
import tkinter.filedialog
import requests, json, csv
from threading import Thread
import time
from os.path import join
import socket as sc
import numpy as np
import tkinter.scrolledtext as st
import serial
import ipaddress
import os
import pickle

class LabeledTextField(ttk.Frame):
    def __init__(
            self,
            *args,
            cmd,
            label_text,
            onFieldEntercmd=None,
            button_text="Submit \u23ce",
            field_text="",
            **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.label = ttk.Label(
            self, 
            text=label_text,
            padding=10
        )
        self.inFieldVar = tkinter.StringVar(value=field_text)
        self.inField = ttk.Entry(
            self, 
            textvariable=self.inFieldVar
        )
        self.submitBtn = ttk.Button(
            self,
            text=button_text,
            command=cmd,
        )
        self.inField.bind(
            "<Return>",
            (
                lambda event: cmd()
            ) if onFieldEntercmd is None else (
                onFieldEntercmd
            )
        )
        self.submitBtn.bind(
            "<Return>",
            (
                lambda event: self.submitBtn.invoke()
            )
        )
        self.label.grid(row=0, column=0)
        self.inField.grid(row= 0, column=1)
        self.submitBtn.grid(row= 0, column=2, padx=3)

        self.get = self.inField.get
    
    def set(self, string):
        print(string + "recieved")
        self.inFieldVar.set(string)

class ScrollableNotebook(ttk.Frame):
    def __init__(self,parent,wheelscroll=False,tabmenu=False,*args,**kwargs):
        ttk.Frame.__init__(self, parent, *args)
        self.xLocation = 0
        self.timer = None
        self.notebookContent = ttk.Notebook(self,**kwargs)
        self.notebookContent.pack(fill="both", expand=True)
        self.notebookTab = ttk.Notebook(self,**kwargs)
        self.notebookTab.bind("<<NotebookTabChanged>>",self._tabChanger)
        if wheelscroll==True: self.notebookTab.bind("<MouseWheel>", self._wheelscroll)
        self.slideFrame = ttk.Frame(self)
        self.slideFrame.place(relx=1.0, anchor="ne", height=45)
        self.menuSpace=30
        if tabmenu==True:
            self.menuSpace=50
            bottomTab = ttk.Label(self.slideFrame, text="\u2630")
            bottomTab.bind("<ButtonPress-1>",self._bottomMenu)
            bottomTab.grid()
        leftArrow = ttk.Label(self.slideFrame, text=" \u276E")
        leftArrow.bind("<ButtonPress-1>",self._leftSlideStart)
        leftArrow.bind("<ButtonRelease-1>",self._slideStop)
        leftArrow.grid(row=0, column=0, sticky="ns")
        rightArrow = ttk.Label(self.slideFrame, text=" \u276F")
        rightArrow.bind("<ButtonPress-1>",self._rightSlideStart)
        rightArrow.bind("<ButtonRelease-1>",self._slideStop)
        rightArrow.grid(row=0, column=1, sticky="ns")
        self.slideFrame.grid_rowconfigure(0, weight=1)
        self.notebookContent.bind("<Configure>", self._resetSlide)
        self.contentsManaged = []

    def _wheelscroll(self, event):
        if event.delta > 0:
            self._leftSlide(event)
        else:
            self._rightSlide(event)

    def _bottomMenu(self, event):
        tabListMenu = Menu(self, tearoff = 0)
        for tab in self.notebookTab.tabs():
            tabListMenu.add_command(label=self.notebookTab.tab(tab, option="text"),command= lambda temp=tab: self.select(temp))
        try:
            tabListMenu.tk_popup(event.x_root, event.y_root)
        finally:
            tabListMenu.grab_release()

    def _tabChanger(self, event):
        try: self.notebookContent.select(self.notebookTab.index("current"))
        except: pass

    def _rightSlideStart(self, event=None):
        if self._rightSlide(event):
            self.timer = self.after(100, self._rightSlideStart)

    def _rightSlide(self, event):
        if self.notebookTab.winfo_width()>self.notebookContent.winfo_width()-self.menuSpace:
            if (self.notebookContent.winfo_width()-(self.notebookTab.winfo_width()+self.notebookTab.winfo_x()))<=self.menuSpace+5:
                self.xLocation-=20
                self.notebookTab.place(x=self.xLocation,y=0)
                return True
        return False

    def _leftSlideStart(self, event=None):
        if self._leftSlide(event):
            self.timer = self.after(100, self._leftSlideStart)

    def _leftSlide(self, event):
        if not self.notebookTab.winfo_x()== 0:
            self.xLocation+=20
            self.notebookTab.place(x=self.xLocation,y=0)
            return True
        return False

    def _slideStop(self, event):
        if self.timer != None:
            self.after_cancel(self.timer)
            self.timer = None

    def _resetSlide(self,event=None):
        self.notebookTab.place(x=0,y=0)
        self.xLocation = 0

    def add(self,frame,**kwargs):
        if len(self.notebookTab.winfo_children())!=0:
            self.notebookContent.add(frame, text="",state="hidden")
        else:
            self.notebookContent.add(frame, text="")
        self.notebookTab.add(ttk.Frame(self.notebookTab),**kwargs)
        self.contentsManaged.append(frame)

    def forget(self,tab_id):
        index = self.notebookTab.index(tab_id)
        self.notebookContent.forget(self.__ContentTabID(tab_id))
        self.notebookTab.forget(tab_id)
        self.contentsManaged[index].destroy()
        self.contentsManaged.pop(index)

    def hide(self,tab_id):
        self.notebookContent.hide(self.__ContentTabID(tab_id))
        self.notebookTab.hide(tab_id)

    def identify(self,x, y):
        return self.notebookTab.identify(x,y)

    def index(self,tab_id):
        return self.notebookTab.index(tab_id)

    def __ContentTabID(self,tab_id):
        return self.notebookContent.tabs()[self.notebookTab.tabs().index(tab_id)]

    def insert(self,pos,frame, **kwargs):
        self.notebookContent.insert(pos,frame, **kwargs)
        self.notebookTab.insert(pos,frame,**kwargs)

    def select(self,tab_id):
##        self.notebookContent.select(self.__ContentTabID(tab_id))
        self.notebookTab.select(tab_id)

    def tab(self,tab_id, option=None, **kwargs):
        kwargs_Content = kwargs.copy()
        kwargs_Content["text"] = "" # important
        self.notebookContent.tab(self.__ContentTabID(tab_id), option=None, **kwargs_Content)
        return self.notebookTab.tab(tab_id, option=None, **kwargs)

    def tabs(self):
##        return self.notebookContent.tabs()
        return self.notebookTab.tabs()

    def enable_traversal(self):
        self.notebookContent.enable_traversal()
        self.notebookTab.enable_traversal()


class DataAquisition(ttk.Frame, Thread):
    def __init__(self, *args, endpoint, **kwargs):
        super().__init__(*args, **kwargs)
        Thread.__init__(self, target=self.aquire, daemon=True)

        self.endpoint = endpoint
        self.delay_ms = 5  # 5ms
        self.aquireDelayField = LabeledTextField(
            self,
            label_text="Aquisition Delay(ms)",
            cmd = lambda: self.set_aquisition_delay(
                float(self.aquireDelayField.get())
            )
        )
        self.aquireDelayField.grid(row=0, column=0)

        self.saveDataParentFrame = ttk.Frame(self)
        self.saveDataParentFrame.grid(row=1, column=0, sticky=tkinter.W)

        self.saveDataCheckButtonVal = tkinter.BooleanVar(value=True)

        self.saveDataCheckButtonLabel = ttk.Label(
            self.saveDataParentFrame,
            text="Save Data"
        )
        self.saveDataCheckButton = ttk.Checkbutton(
            self.saveDataParentFrame,
            variable= self.saveDataCheckButtonVal,
            command=lambda: self.enable_data_save_frame(
                self.saveDataCheckButtonVal
            )
        )
        self.saveDataCheckButtonLabel.grid(row=0, column=0, padx=10)
        self.saveDataCheckButton.grid(row=0, column=1, padx=5, sticky="W")
        self.dataSaveDir = join(__file__, "../../temp")

        self.data_text_var = tkinter.StringVar(value="----")
        self.data_text = ttk.Label(
            self.saveDataParentFrame,
            textvariable=self.data_text_var,
            
        )

        self.saveDataFrame = ttk.Frame(
            self.saveDataParentFrame
        )

        self.saveDataFrame.grid(row=1, column=0, columnspan=2)
        self.setup_data_save_frame()

        self.saveDataParentFrame.grid_columnconfigure(1, weight=1)
        self.saveDataParentFrame.grid_rowconfigure(2, weight=1)
        self.data_callbacks = []

        self.data_text.grid(row=2)

        # Start polling
        self.start()

    def set_aquisition_delay(self, delay_ms):
        self.delay_ms = delay_ms

    def enable_data_save_frame(self, save: tkinter.BooleanVar):
        if save.get():
            self.saveDataFrame.grid(row=1, column=0, columnspan=2)
        else:
            self.saveDataFrame.grid_forget()

    def setup_data_save_frame(self):
        self.dataSaveDirPrompt = LabeledTextField(
            self.saveDataFrame,
            label_text="Save Folder",
            button_text="Browse",
            cmd=lambda: self.set_data_save_dir(
                tkinter.filedialog.askdirectory()
            ), 
            onFieldEntercmd=lambda event: self.set_data_save_dir(
                self.dataSaveDirPrompt.get()
            )
        )
        self.dataSaveDirPrompt.grid()
    def set_data_save_dir(self, saveDir):
        if saveDir:
            self.dataSaveDir = saveDir
            self.dataSaveDirPrompt.set(saveDir)
    
    def aquire(self):
        print("started aquire")

        sock = sc.socket(sc.AF_INET, sc.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 65432))
        # Store in new file on each run
        currentFile = time.strftime(
            "DTTS_LOG_%Y_%m_%d_%H_%M_%S.csv"
        )
        while True:
            # try:
            #     res = requests.get(
            #         f"{self.endpoint}/get_data",
            #         timeout=1
            #     )
            # except:
            #     print("Failed to contact arduino")
            #     continue
            # if res.status_code == 200:
            #     self.data = None
            #     for i in range(len(res.text)-1, -1, -1):
            #         if res.text[i] != "}":
            #             continue
            #         self.data = json.loads(res.text[:i+1])
            #         break
            #     self.invoke_data_callbacks()
            #     if self.saveDataCheckButtonVal.get():
            #         self.write_data(currentFile, self.data)

            try:
                data, addr = sock.recvfrom(2046) # buffer size is 1024 bytes
                self.data = json.loads(data.decode())
                # print(self.data)
                self.invoke_data_callbacks()
                if self.saveDataCheckButtonVal.get():
                    self.write_data(currentFile, self.data)
                    self.data_text_var.set(json.dumps(self.data, indent=4))
            except Exception as e:
                print(f"Unable to recieve or decode: {e}")
            time.sleep(self.delay_ms / 1000.0)
    def attach_data_callbacks(self, *callbacks):
        for callback in callbacks:
            self.data_callbacks.append(callback)

    def invoke_data_callbacks(self):
        if self.data is None or len(self.data) == 0:
            return
        for callback in self.data_callbacks:
            callback(self.data)
    def write_data(self, fileName, data):
        try:
            with open(join(self.dataSaveDir, fileName), "a", newline="") as file:
                writer = csv.writer(file)
                if len(data) < 1:
                    print("Could not write. No data")
                    return
                data_keys = data.keys()
                if file.tell() == 0:
                    writer.writerow(data_keys)
                writer.writerow([data[i] for i in data_keys])
        except:
            print(
                "Unable to save data. "
                f"Could not save file at {fileName}"
            )
        
class ESC(ttk.Frame, Thread):
    def __init__(self, *args, endpoint, **kwargs):
        super().__init__(*args, **kwargs)
        Thread.__init__(self, target=self.send_throttle_command, daemon=True)

        self.throttleProfile = None
        self.profileStartTime = 0
        self.runFromProfile = False

        self.endpoint = endpoint
        self.esc_throttle = tkinter.DoubleVar(value=0)
        self.throttleLabel = ttk.Label(
            self,
            text="Throttle   ",
            font=("consolas", 12)
        )
        self.throttleLabel.grid(row=0, column=0, padx=5, pady=3)
        self.escSlider = ttk.Scale(
            self,
            from_=0,
            to=100,
            orient=tkinter.HORIZONTAL,
            command=self.update_esc_throttle,
            variable=self.esc_throttle,
            length=250,
        )
        self.escSlider.grid(row=0, column=1, sticky="ew", padx=5)

        self.stopESCButton = ttk.Button(
            self,
            command=self.stop_esc,
            text="Stop ESC"
        )
        self.stopESCButton.grid(column=0, columnspan=2, sticky="ew", padx=3)

        self.calibrationFrame = ttk.Frame(
            self
        )
        self.beginCalibrationButton = ttk.Button(
            self.calibrationFrame,
            command=lambda: self.update_esc_throttle(100),
            text="Begin Calibration"
        )
        self.endCalibtraionButton = ttk.Button(
            self.calibrationFrame,
            command=lambda: self.update_esc_throttle(0),
            text="Finish Calibration"
        )
        self.calibrationFrame.grid(
            columnspan=2, 
            padx=3,
            pady=3,
            sticky="nsew"
        )
        self.calibrationFrame.columnconfigure(
            (0,1),
            weight=1,
            uniform="calibrationFrame"
        )
        self.beginCalibrationButton.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0,1.5)
        )
        self.endCalibtraionButton.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(1.5,0)
        )

        self.runProfileFrame = ttk.Frame(
            self
        )
        self.selectProfileButton = ttk.Button(
            self.runProfileFrame,
            text="Select Throttle Profile",
            command=lambda: self.read_profile(tkinter.filedialog.askopenfile(
                filetypes=[("csv(*.csv)", "*.csv")]
            ))
        )
        self.runProfileButton = ttk.Button(
            self.runProfileFrame,
            text="Run Profile",
            command=self.run_profile
        )
        self.runProfileFrame.grid(
            columnspan=2,
            padx=3,
            sticky="nsew"
        )
        self.selectProfileButton.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 1.5)
        )
        self.runProfileButton.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(1.5, 0)
        )
        self.runProfileFrame.grid_columnconfigure(
            (0,1),
            weight=1,
            uniform="runProfileFrame"
        )

        self.grid_columnconfigure(1, weight=1)
        self.start()

    def send_throttle_command(self):
        currentProfileStep = None
        while True:
            # Run Throttle Profile
            nextThrottleCommand = self.esc_throttle.get() / 100.0
            if self.runFromProfile and self.throttleProfile is not None:
                # Determine if we should go to next throttle setting
                if (
                    currentProfileStep is None or
                    currentProfileStep[0] + self.profileStartTime <= time.time() * 1000
                ):
                    currentProfileStep = next(self.throttleProfile, None)
                # Reset at the end of the file
                if currentProfileStep is None:
                    self.runFromProfile = False
                else:
                    nextThrottleCommand = currentProfileStep[1] / 100.0
                    print(
                        f"Current Profile Step: t={currentProfileStep[0]:.0f}ms"
                        f" throttle={currentProfileStep[1]:.1f}%"
                    )
            else:
                currentProfileStep = None

            try:
                res = requests.post(
                    f"{self.endpoint}/esc_set_throttle?p="
                    f"{nextThrottleCommand}",
                    timeout=1
                )
            except:
                print("Failed to set throttle")
            time.sleep(20/1000)
    def update_esc_throttle(self, percent_throttle):
        self.esc_throttle.set(
            max(0.0, min(100.0, float(percent_throttle)))
        )
    def run_profile(self):
        if self.throttleProfile is None:
            print("No Profile Selected!")
            return
        print("Running Profile")
        # Turn off motors after profile finishes
        self.esc_throttle.set(0)
        self.profileStartTime = time.time() * 1000
        self.runFromProfile = True
    def read_profile(self, file):
        if file is None:
            print("No file!")
            return
        throttleProfile = []
        reader = csv.reader(file)
        for row in reader:
            try:
                throttleProfile.append(
                    [float(i) for i in row]
                    )
            except:
                print("invalid profile!")
                print(row)
        file.close()
        if len(throttleProfile) > 0:
            self.throttleProfile = self.generate_profile_iterator(
                throttleProfile
            )
            self.runFromProfile = False
            self.update_esc_throttle(0)
    def stop_esc(self):
        self.update_esc_throttle(0)
        self.runFromProfile = False
        self.throttleProfile = None
    def generate_profile_iterator(self, profile):
        for row in profile:
            yield row


class Power(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.current_readout_var = tkinter.StringVar(value="0")
        self.current_readout = ttk.Label(
            self,
            textvariable=self.current_readout_var,
            font=("Consolas", 16)
        )
        self.voltage_mode_var = tkinter.StringVar(value="25V  ")
        self.voltage_mode_switch_label = ttk.Label(
            self,
            text="Voltage Mode: ",
            font=("Consolas", 16)
        )
        self.voltage_mode_switch = ttk.OptionMenu(
            self,
            self.voltage_mode_var,
            *("25V  ", "50V  ", "25V  ")
        )
        self.voltage_readout_var = tkinter.StringVar(value="0V")
        self.voltage_readout = ttk.Label(
            self,
            textvariable=self.voltage_readout_var,
            font=("Consolas", 16)
        )
        self.voltage_mode_switch_label.grid(row=0, column=0, sticky="W")
        self.voltage_mode_switch.grid(row = 0, column=1, sticky="W", padx="5")
        self.voltage_readout.grid(sticky="W")
        self.current_readout.grid(sticky="W")
        self.mov_avg_buff = []

    def set_current_readout(self, data):
        if len(self.mov_avg_buff) > 50:
            self.mov_avg_buff.pop(0)
        fixed_data = data["current_sense"]
        # fixed_data += (fixed_data*0.0128 - 0.0501) + 4.04
        self.mov_avg_buff.append(fixed_data)
        self.current_readout_var.set(f"Current: {np.mean(self.mov_avg_buff):.3f}A")

    def set_voltage_readout(self, data):
        if "25" in self.voltage_mode_var.get():
            self.voltage_readout_var.set(
                f"Voltage: {self.calibrate_voltage(data['voltage_sense'] * 25):.3f}V")
        else:
            self.voltage_readout_var.set(
                f"Voltage: {self.calibrate_voltage(data['voltage_sense'] * 50):.3f}V")

    def calibrate_voltage(self, value):
        if "50" in self.voltage_mode_var.get():
            return value + 0.0508*value + 0.692
        else:
            return value + 0.0448*value + 0.382
        

class Serial(ttk.Frame, Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Thread.__init__(self, target=self.update, daemon=True)
        self.runThread = True

        self.send = False

        self.comPort = LabeledTextField(
            self,
            label_text="COM Port: ",
            onFieldEntercmd=self.restart_serial,
            cmd=self.restart_serial,
            button_text="Submit",
            field_text="COM18"
        )
        
        self.send_data_frame = ttk.Frame(
            self
        )
        self.send_data_var = tkinter.StringVar(value='')
        self.send_data_box = ttk.Entry(
            self.send_data_frame,
            textvariable=self.send_data_var
        )
        self.send_data_button = ttk.Button(
            self.send_data_frame,
            command=self.send_data,
            text="Send!"
        )
        self.send_data_frame.grid_columnconfigure(0, weight=8)
        self.send_data_frame.grid_columnconfigure(1, weight=2)
        self.send_data_box.grid(column=0, row=0, sticky="nsew")
        self.send_data_button.grid(column=1, row=0, sticky="nsew")
        
        self.textbox = st.ScrolledText(self, wrap=tkinter.WORD)
        self.comPort.grid()
        self.textbox.grid()
        self.send_data_frame.grid()

        self.connection_parameters = {}
        
        self.start()


    def update(self):
        while True:
            ser = None
            try:
                ser = serial.Serial(
                    port=self.comPort.get(),
                    baudrate=115200, # Arduino uses this
                    timeout=2
                )
                while self.runThread and ser is not None:
                    text = ser.read_all().decode()
                    if(text):
                        try:
                            ip = ipaddress.IPv4Address(text.strip())
                            print(ip)
                            if ip.is_private:
                                print("Found valid ip: " + str(ip))
                                self.connection_parameters["IP"] = str(ip)
                                with open(
                                    os.path.join(__file__, "..", "dtts.cfg"),
                                    "wb"
                                ) as file:
                                    pickle.dump(self.connection_parameters, file)
                        except:
                            pass
                        self.update_text(text)
                    if self.send:
                        # Write some data
                        ser.write(self.send_data_var.get().encode())
                        self.send = False
                # time.sleep(0.05)
                self.runThread = True
                ser.close()
            except Exception as e:
                print(e)
            time.sleep(1)

    def restart_serial(self, _ = ""):
        self.runThread = False

    def update_text(self, msg):
        self.textbox.configure(state='normal')
        self.textbox.insert(tkinter.END, chars=msg)
        self.textbox.configure(state='disabled')

    def send_data(self):
        self.send = True
            

