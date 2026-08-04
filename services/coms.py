import glob
import subprocess
import serial


BOARD_MAPPING = {

    "NanoPC-T3": {
        "FC": "3",
        "DET": "4",
        "ATG": "1",
    },

    "NanoPC-T4": {
        "FC": "2",
        "DET": "6",
        "ATG": "3",
    },

    "NanoPC-T6": {
        "FC": "1",
    },
}


class ComDevice:
    def __init__(self):
        self.device = ""
        self.type = ""
        self.driver = ""
        self.vendor = ""
        self.model = ""
        self.serial = ""
        self.path = ""
        self.usb_port = ""
        self.name = ""
        self.connected = False


class ComStatus:
    def __init__(self):
        self.devices = []


def get_coms_details():

    return {
        "lcd": get_device_status("LCD"),
        "fc": get_device_status("FC"),
        "atg": get_device_status("ATG"),
    }



def get_devices():

    status = ComStatus()

    device_list = []

        
    # USB devices
    device_list.extend(glob.glob("/dev/ttyUSB*"))
    device_list.extend(glob.glob("/dev/ttyACM*"))


    for device in device_list:

        info = get_device(device)

        if info:
            status.devices.append(info)


    # # # Check ATG
    # atg = get_atg_status()

    # if atg == "Connected":

    #     atg_device = ComDevice()

    #     atg_device.device = "/dev/ttyS4"
    #     atg_device.type = "UART"
    #     atg_device.name = "ATG"
    #     atg_device.connected = True

    #     status.devices.append(atg_device)

    status.total = len(status.devices)

    return status

        

def get_device(device):

    com = ComDevice()

    com.device = device
    com.connected = True


    if device.startswith("/dev/ttyUSB"):
        com.type = "USB Serial"

    elif device.startswith("/dev/ttyACM"):
        com.type = "USB ACM"


    result = subprocess.run(
        [
            "udevadm",
            "info",
            "--query=property",
            "--name",
            device,
        ],
        capture_output=True,
        text=True,
    )


    for line in result.stdout.splitlines():

        if "=" not in line:
            continue


        key, value = line.split("=", 1)


        if key == "ID_VENDOR":
            com.vendor = value

        elif key == "ID_MODEL":
            com.model = value

        elif key == "ID_SERIAL_SHORT":
            com.serial = value

        elif key == "ID_PATH":
            com.path = value

        elif key == "ID_USB_DRIVER":
            com.driver = value

        elif key == "DEVPATH":

            com.usb_port = get_usb_port(value)


    com.name = identify_device(com.usb_port)

    return com



def run_command(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
        )

        return result.stdout.strip()

    except Exception:
        return ""




def get_atg_status():


    # try:

    #     # Use python command to read the UART
    #     output = run_command([
    #         "sudo",
    #         "python3",
    #         "-c",
    #         "import serial; ser=serial.Serial('/dev/ttyS4',19200,timeout=1); print('Connected' if ser.read(100) else 'Not Found'); ser.close()"
    #     ])


    #     if "Connected" in output:
    #         return "Connected"

    #     elif "Not Found" in output:
    #         return "Not Found"

    #     return "Unknown"


    # except Exception:

    return "Unknown"
        

def get_usb_port(devpath):

    board = get_board_type()


    # NanoPC-T3
    # Example:
    # 2-1.3
    # 2-1.4

    if board == "NanoPC-T3":

        parts = devpath.split("/")

        for part in parts:

            if "." in part and "-" in part:

                return part.split(".")[-1]


    # NanoPC-T4
    # Example:
    # usb6/6-1
    # usb2/2-1

    elif board == "NanoPC-T4":

        parts = devpath.split("/")

        for part in parts:

            if part.startswith("usb"):

                return part.replace("usb", "")


    return ""



def get_board_type():

    try:

        with open("/proc/device-tree/model", "r") as file:

            model = file.read().replace("\x00", "")


    except:

        return "Unknown"



    if "NanoPC-T3" in model:
        return "NanoPC-T3"

    elif "NanoPC-T4" in model:
        return "NanoPC-T4"

    elif "NanoPC-T6" in model:
        return "NanoPC-T6"


    return "Unknown"



def identify_device(port):

    board = get_board_type()

    mapping = BOARD_MAPPING.get(board, {})


    for name, usb_port in mapping.items():

        if port == usb_port:
            return name


    return "Unknown"



def get_device_status(name):

    status = get_devices()


    for device in status.devices:

        if device.name == name:

            return "Connected"


    return "Not Found"



if __name__ == "__main__":


    print("Board:")
    print(get_board_type())


    print()


    devices = get_devices()


    for device in devices.devices:

        print("--------------------------------")
        print("Device:", device.device)
        print("Name:", device.name)
        print("Port:", device.usb_port)
        print("Vendor:", device.vendor)
        print("Model:", device.model)
        print("Serial:", device.serial)