import sys
import os
import serial
import time
import logging

#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flash_load import FlashLoad

PORT = "/dev/ttyS0"
BAUD = 230400

BITSTREAM_FILE = "11B_operation_0362905b6d789a_981735f482b6d4_download.bin"

logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG
    format="%(asctime)s - %(levelname)s - %(message)s",  # Optional format
)

try:
    serial_port = serial.Serial(PORT, BAUD, timeout=1)
except serial.SerialException as e:
    err = {"status": False, "msg": f"Could not open port: {e}"}
    print(err)
    sys.exit(1)
fl = FlashLoad(serialport=serial_port, timeout=1)

load_result = fl.load_bitstream_file(BITSTREAM_FILE)
print(f"Result:{load_result['status']}, {load_result['msg']}")
# wr = fl.write_image_to_flash("operation")
# print(f"Result:{wr['status']}, {wr['msg']}")

fl.init_flash_operation("operation", "read", 257)
command_loop(fl)