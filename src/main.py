import requests
from tkinter import Tk, ttk
import tkinter
import sv_ttk
import ctypes, os  # To check if this is running as root
import keyboard as kb
from components import *
import os
import pickle

BOARD_IP = "10.17.187.96"

class App(Tk):
    def __init__(self, *args, endpoint = "localhost", **kwargs):
        super().__init__(*args, **kwargs)

        self.endpoint = endpoint
        self.serial = None

        sv_ttk.set_theme("dark")
        self.title("SUAS Dynamic Thrust Test Stand")

        endpoint_scan = Thread(target=self.scan_endpoint, daemon=True)
        endpoint_scan.start()


        self.Header = ttk.Label(self, text="SUAS DTTS", font=("Consolas", 25))
        self.Header.grid(row=0, column=0)

        self.parentNotebook = ScrollableNotebook(self, wheelscroll=True)
        self.parentNotebook.grid(row=1, column=0, sticky="EW")

        self.general_frame = ttk.Frame(
            self.parentNotebook,
        )
        self.general_frame.pack()


        self.pollingRateField = LabeledTextField(
            self.general_frame, 
            label_text="Polling Delay",
            cmd = lambda: requests.post(
                f"{self.endpoint}/set_blink_delay?t="
                f"{float(self.pollingRateField.get())}"
            )
        )
        self.pollingRateField.grid(sticky=tkinter.E)
        self.timeSyncField = LabeledTextField(
            self.general_frame,
            label_text="Sync Time(ms)",
            cmd = lambda: requests.post(
                f"{self.endpoint}/sync_time?t="
                f"{float(self.timeSyncField.get())}"
            )
        )
        self.burnPrefs = ttk.Button(
            self.general_frame,
            text="Burn Config",
            command=lambda: print(requests.get(
                f'{self.endpoint}/save_prefs',
                timeout=1
            ).text)
        )
        self.wipePrefsButton = ttk.Button(
            self.general_frame,
            text="Wipe Preferences",
            command=lambda: requests.get(
                f"{self.endpoint}/wipe_prefs"
            )
        )
        self.timeSyncField.grid(sticky=tkinter.E)
        self.burnPrefs.grid(sticky="ew", pady=3)
        self.wipePrefsButton.grid(sticky="ew")
        self.general_frame.grid_columnconfigure((0, 1), weight=1)
        self.load_cell_frame = ttk.Frame(
            self.parentNotebook
        )
        self.load_cell_frame.pack()

        self.calibrateLoadCellField = LabeledTextField(
            self.load_cell_frame,
            label_text="Calibrate Load Cell",
            cmd = lambda: requests.post(
                f"{self.endpoint}/calibrate_load_cell?weight="
                f"{float(self.calibrateLoadCellField.get())}"
            )
        )
        self.calibrateLoadCellField.grid(sticky=tkinter.E)

        self.tareLoadCell = ttk.Button(
            self.load_cell_frame,
            text=("Tare \u21ba"),
            command=lambda: requests.get(
                f"{self.endpoint}/tare_load_cell"
            )
        )
        self.tareLoadCell.grid(sticky="ew", padx=3)

        self.LoadCellValueLabel = ttk.Label(
            self.load_cell_frame,
            textvariable=(load_cell_var:=tkinter.StringVar(
                value="Load Cell: ---"
            )),
            font=("consolas", 12)
        )
        self.LoadCellValueLabel.grid(sticky="ew", padx=5)

        self.dataAquisitionFrame = ttk.Frame(
            self.parentNotebook
        )
        self.dataAquisitionFrame.pack()

        self.dataAquisition = DataAquisition(
            self.dataAquisitionFrame,
            endpoint=self.endpoint
        )
        self.dataAquisition.attach_data_callbacks(
            lambda data: load_cell_var.set(
                f"Load Cell: {data.get('load_cell', '---')}"
            )
        )
        self.dataAquisition.pack()


        self.estop = ttk.Button(
            self,
            command=self.handle_estop,
            text="----ESTOP----",
            
        )
        self.estop.grid(sticky="ew", pady=(3, 0))
        kb.add_hotkey("ctrl+space", self.handle_estop)

        self.esc_control = ESC(
            self.parentNotebook,
            endpoint=self.endpoint
        )
        self.esc_control.pack(expand=True, fill="both", padx=3, pady=3)

        self.power_frame = ttk.Frame(
            self.parentNotebook
        )
        self.power_frame.pack()
        self.power = Power(
            self.power_frame
        )
        self.dataAquisition.attach_data_callbacks(
            self.power.set_current_readout,
            self.power.set_voltage_readout
        )
        self.power.grid(padx=3)

        self.serial_frame = ttk.Frame(
            self.parentNotebook
        )
        self.serial = Serial(self.serial_frame)
        self.serial_frame.pack()
        self.serial.grid()

        # self.grid_propagate(False)
        self.parentNotebook.add(self.general_frame, text="General")
        self.parentNotebook.add(self.dataAquisitionFrame, text="Data Aquisition")
        self.parentNotebook.add(self.load_cell_frame, text="Load Cell")
        self.parentNotebook.add(self.esc_control, text="ESC")
        self.parentNotebook.add(self.power_frame, text="Power")
        self.parentNotebook.add(self.serial_frame, text="Serial")
        self.resizable(False, False)

    def handle_estop(self):
        try:
            res = requests.get(
                f"{self.endpoint}/esc_estop",
                timeout=1
            )
            print(res.text)
        except:
            print("ESTOP FAILED!")
            print("EXITING PROGRAM!")
            self.quit()
    
    def reset_udp_stream(self):
        stop = False
        while not stop:
            print("Waiting for Arduino...")
            try:
                assert requests.get(
                    f'{self.endpoint}/reset_udp',
                    timeout=1
                ).status_code == 200
                stop = True

                print("Cleared UDP Stream!")
            except:
                pass

    def scan_endpoint(self):
        newEndpoint = False
        lastIP = ""
        while True:
            time.sleep(1)
            connection_params = None
            try:
                with open(os.path.join(__file__, '..', 'dtts.cfg'), 'rb') as file:
                    connection_params = pickle.load(file)
            except Exception as e:
                print(e)
            if connection_params is not None and "IP" in connection_params:
                newEndpoint = connection_params["IP"] != lastIP
                lastIP = connection_params["IP"]
            if newEndpoint:
                self.endpoint = (
                    f"http://{connection_params['IP']}:80"
                )
                self.esc_control.endpoint = self.endpoint
            try: 
                if newEndpoint and requests.get(
                    f"{self.endpoint}",
                    timeout=1
                ).status_code == 200:
                    self.reset_udp_stream()
            except:
                print("No Endpoint; Rescanning...")

if __name__ == "__main__":
    try:
        is_admin = os.getuid() == 0
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    runProgram = False
    if not is_admin:
        confirm = input(
            "WARNING: Not running as root/administrator.\n"
            "This may prevent the estop shortcut from working.\n"
            "Confirm to proceed? (y/n): "
        )
        if confirm.lower() == "y" or confirm.lower() == "yes":
            runProgram = True
    else:
        runProgram = True
    if runProgram:
        a = App(endpoint=f"http://{BOARD_IP}:80")
        a.mainloop()
