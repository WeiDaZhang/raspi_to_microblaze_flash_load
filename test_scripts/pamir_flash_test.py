import sys
import os
import serial
import time
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from flash_load import FlashLoad

def main():
    filename = "pamir_comms_test.py"

    serial_port = serial.Serial('/dev/ttyS0', 230400, timeout=2)
    flash_load = FlashLoad(serialport=serial_port, timeout=1)
    flash_load.load_bitstream_file(file_name=filename)
    
    data = f".SpiFshEr 0x00000000\n" 
    serial_port.write(bytes(data, 'utf-8'))
    tic = time.time()
    while time.time() < tic + 5:
        print(f"ack from microblaze Erase: {serial_port.readline()}")
        time.sleep(1)
    data = f".SpiFshRd 0x00000000\n" 
    serial_port.write(bytes(data, 'utf-8'))
    tic = time.time()
    while time.time() < tic + 5:
        print(f"ack from microblaze Read after Erase: {serial_port.readline()}")
        time.sleep(1)
    data = f".SpiFshWr 0x00000000 0x{hex_output}\n" 
    serial_port.write(bytes(data, 'utf-8'))
    tic = time.time()
    while time.time() < tic + 5:
        print(f"ack from microblaze Write: {serial_port.readline()}")
        time.sleep(1)
    data = f".SpiFshRd 0x00000000\n" 
    serial_port.write(bytes(data, 'utf-8'))
    tic = time.time()
    while time.time() < tic + 5:
        print(f"ack from microblaze Read after Write: {serial_port.readline()}")
        time.sleep(1)

if __name__ == "__main__":
    main() 
