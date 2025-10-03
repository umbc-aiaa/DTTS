# SUAS DTTS Arduino Code and Client Software

## To set up the arduino...
- Create a "src" folder under the "Arduino_Server" directory
- Create a "credentials.h" file and paste in the following:
    ```
    #define SSID "<Your SSID>"
    #define PASSWORD "<Your Passowrd>"
    ```
- Replace `"<Your SSID>"` and `"<Your Password>"` with the correct values
- Open the "Arduino_Server" sketch folder in the Arduino IDE and deploy the code

## To set up the GUI...
> Note that the GUI will be packaged into an .exe in production. These instructions are for the development phase.
- crate a virtual environment in the project root directory ("SUAS_THRUSTTEST") with the following `python -m venv <path_to_root_dir>`.
    - If you are already in the "SUAS_THRUSTTEST" directory, `<path_to_root_dir>` is just `.`. 
- Activate the virtual environment by running `source Scripts/activate` on Windows or `source bin/activate` on Linux.
- Install the dependencies by running `pip install -r requirements.txt`
- Run the main.py file: `python src/main.py` or `python3 src/main.py`
- You must run as administrator or root
    - This is to ensure the estop shortcut(`ctrl+space`) works