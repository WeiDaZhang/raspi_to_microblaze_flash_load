import sys
import os
import serial
import time
import logging

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flash_load import FlashLoad

PORT = "/dev/ttyS0"
BAUD = 230400

BITSTREAM_FILE = "11B_operation_0362905b6d789a_981735f482b6d4_download.bin"

logging.basicConfig(
    level=logging.DEBUG,  # Set the logging level to DEBUG
    format="%(asctime)s - %(levelname)s - %(message)s",  # Optional format
)


def command_loop(fl: FlashLoad, status_check_timeout: float = 0.5) -> None:
    help_text = "Commands: load write read prog  pause  resume  abort  quit/exit"
    print(help_text)

    while True:
        cmd = input("> ").strip().lower()

        # ---------- load ----------
        if cmd == "load":
            load_result = fl.load_bitstream_file(BITSTREAM_FILE)
            print(f"Result:{load_result['status']}, {load_result['msg']}")

        # ---------- write ----------
        if cmd == "write":
            fl.init_flash_operation(
                operation_type="write",
                image_type="operation",
            )

        # ---------- read ----------
        if cmd == "read":
            fl.init_flash_operation(
                operation_type="read",
                image_type="operation",
            )

        # ---------- progress ----------
        if cmd == "prog":
            # self.events["progress"].set()
            for msg in fl.flash_operation_status(status_check_timeout):
                print(msg["msg"])
            continue

        # ---------- pause / resume ----------
        if cmd == "pause":
            fl.set_flash_operation_pause()
            print("Pause requested. Waiting for resume command.")
            continue

        if cmd == "resume":
            fl.set_flash_operation_resume()
            print("Resume requested.")
            continue

        # ---------- abort ----------
        if cmd == "abort":
            fl.set_flash_operation_abort()
            print("Abort requested.")
            continue

        # ---------- quit ----------
        if cmd in {"quit", "exit"}:
            break

        print(help_text)


def main():
    try:
        serial_port = serial.Serial(PORT, BAUD, timeout=1)
    except serial.SerialException as e:
        err = {"status": False, "msg": f"Could not open port: {e}"}
        print(err)
        sys.exit(1)
    fl = FlashLoad(serialport=serial_port, timeout=1)

    command_loop(fl)


if __name__ == "__main__":
    main()
