import time
import os
import sys
from typing import Literal

from serial_commport.Pamir_serial_basic import PamirSerial
# It turns out "flash_erase", "flash_write", "flash_read" has been provided by [Meenu S]
# You would want to override them and potentially encapsulate them



class FlashLoad(PamirSerial):
    @staticmethod
    def read_binary_to_hex(filename, max_bytes=256) -> dict:
        return_dict = {"status": True, "msg": None}
        try:
            with open(filename, 'rb') as f:
                data = f.read(max_bytes)  # Read up to max_bytes to avoid memory issues
                hex_str = data.hex()  # Convert bytes to hex string
                return_dict["data"] = hex_str
                return return_dict
        except FileNotFoundError:
            return_dict["status": False, "msg": "Error: File not found"]
        except Exception as e:
            return_dict["status": False, "msg": f"Error: {str(e)}"]
        return return_dict

    def load_bitstream_file(self, file_name: str):
        # check if extension provided in the file name
        # check if correct extensions
        read_file_content = self.read_binary_to_hex(file_name)
        if not read_file_content["status"]:
            return read_file_content
        else:
            # check file size
            # check syncronisation code "AA995566" exists, etc.,
            self.bitstream = read_file_content["data"]
            pass

    def write_to_flash(self, image_type=Literal["golden","operation"]):
        return_dict = {"status": True, "msg": None}
        if not hasattr(self, "bitstream"):
            return_dict["status": False]
            return_dict["msg": "Valid bitstream is not loaded."]
            return
        # check image_type
        # check file length

        # Erase loop
        while True:
            # generating start address based on image_type
            #addr = 0x01000000 / 0x0000000
            #0x00000000 -> 0x00FFFFFF /4k
            #self._erase()
            #self.get_flash_status()
            break

        # Write loop
        while True:
            #page = file_content[0, -1, 256]
            #self._write(self.page, addr)
            break
        
    def read_from_flash(self, image_type=Literal["golden","operation"]):
        pass
        
