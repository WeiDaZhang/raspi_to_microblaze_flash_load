import sys

import serial
from flash_load import FlashLoad
PORT  = "/dev/ttyS0"
BAUD  = 230400

try:
    serial_port = serial.Serial(PORT, BAUD, timeout=1)
except serial.SerialException as e:
    err = {
        "status": False,
        "msg": f"Could not open port: {e}"
    }
    print(err)
    sys.exit(1)
fl = FlashLoad(serialport=serial_port, timeout=1)
load_result = fl.load_bitstream_file("app.bin")
print(f"Result:{load_result['status']}, {load_result['msg']}")
res = fl.read_flash_id()
if not res["status"]:
    print(res["msg"])
    sys.exit(1)
wr = fl.write_to_flash("operation")
print(f"Result:{wr['status']}, {wr['msg']}")
rd = fl.read_from_flash("operation", True)
print(f"Result:{rd['status']}, {rd['msg']}")
