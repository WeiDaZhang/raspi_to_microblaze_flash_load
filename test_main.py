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
    exit(1)
fl = FlashLoad(serialport=serial_port, timeout=1)
result = fl.write_to_flash("app.bin", "operation")
print(f"Result:{result["status"]}, {result["msg"]}")
rd = fl.read_from_flash("operation", True)
print(f"Result:{rd["status"]}, {rd["msg"]}")
