import time
import os
import sys
import serial
from typing import Literal

from serial_commport.Pamir_serial_basic import PamirSerial
# It turns out "flash_erase", "flash_write", "flash_read" has been provided by [Meenu S]
# You would want to override them and potentially encapsulate them
FLASH_PAGE_SIZE         = 256          # bytes  per program-page
FLASH_SECTOR_SIZE       = 0x10000      # 64 KiB per sector
FLASH_BASE_GOLDEN_BYTES = 0x00000000
MAX_SIZE_BYTES = 0x00F50000
FLASH_MAX_GOLDEN_BYTES  = 0x00F50000
FLASH_BASE_OPERATION_BYTES = 0x01000000
FLASH_MAX_OPERATION_BYTES = 0x01F50000
FLASH_WIP_TIMEOUT_SEC   = 10.0
FLASH_POLL_INTERVAL_SEC = 0.05

class FlashLoad(PamirSerial):
    @staticmethod
    def read_binary_to_hex(filename, max_bytes=FLASH_PAGE_SIZE) -> dict:
        return_dict = {"status": True, "msg": None}
        hex_pages = []
        try:
            with open(filename, 'rb') as f:
                while True:
                    data = f.read(max_bytes)
                    if not data:
                        break
                    hex_pages.append(data.hex())
                return_dict["data"] = hex_pages
                return return_dict
        except FileNotFoundError:
            return_dict["status"] = False
            return_dict["msg"] = "Error: File not found"
        except Exception as e:
            return_dict["status"] = False
            return_dict["msg"] = f"Error: {str(e)}"
        return return_dict

    def load_bitstream_file(self, file_name: str, max_size_bytes=MAX_SIZE_BYTES):
        # check if extension provided in the file name
        if '.' not in file_name:
            return {"status": False, "msg": "No file extension provided."}
        # check if correct extensions
        allowed_exts = [".bit", ".bin" , ".txt"]
        _, ext = os.path.splitext(file_name)
        if ext.lower() not in allowed_exts:
            return {"status": False, "msg": f"Unsupported file extension: {ext}. Allowed extensions: {', '.join(allowed_exts)}"}

        if not os.path.isfile(file_name):
            return {"status": False, "msg": "Error: File not found."}

        # check size of the file
        file_size = os.path.getsize(file_name)
        if file_size > max_size_bytes:
            return {"status": False,
                "msg": f"Error: File too large ({file_size} bytes). Max allowed is {max_size_bytes} bytes."
            }
        print(f"Size of the file：{file_size} bytes")

        return_dict = self.read_binary_to_hex(file_name)
        if not return_dict["status"]:
            return return_dict
        else:
            # check syncronisation code "AA995566" exists, etc.,
            #
            # with open(file_name, 'rb') as f:
            #     header = f.read(4).hex()
            #     if header.lower() != "aa995566":
            #         return {"status": False, "msg": f"Missing synchronisation code AA995566. First 4 bytes:{header.lower()}"}
            self.bitstream = return_dict["data"]
            return return_dict

    def write_to_flash(self, image_type: Literal["golden","operation"]="operation"):
        return_dict = {"status": True, "msg": None}
        if not hasattr(self, "bitstream"):
            return_dict["status"] = False
            return_dict["msg"] = "Valid bitstream is not loaded."
            return return_dict

        # check image_type
        if image_type == "golden":
            base_address = FLASH_BASE_GOLDEN_BYTES
            max_address = FLASH_MAX_GOLDEN_BYTES
        elif image_type == "operation":
            base_address = FLASH_BASE_OPERATION_BYTES
            max_address = FLASH_MAX_OPERATION_BYTES
        else:
            return_dict["status"] = False
            return_dict["msg"] = "Invalid image_type. Use 'golden' or 'operation'."
            return return_dict

        # Erase loop
        print("Erasing sectors...")
        self.flash_write_enable()
        for erase_addr in range(base_address, max_address, FLASH_SECTOR_SIZE):
            print(f"Erasing sector at 0x{erase_addr:08X}")
            try:
                self.flash_erase(erase_addr)
                start = time.time()
                while self.flash_read_status() & 0x01:  # check flash status
                    if time.time() - start > FLASH_WIP_TIMEOUT_SEC:
                        raise TimeoutError("Flash busy > 10 s during erase")
                    time.sleep(FLASH_POLL_INTERVAL_SEC)
            except TimeoutError:
                return_dict["status"] = False
                return_dict["msg"] = "Flash stays busy for > 10 s, aborting"
                return return_dict
            except Exception as e:
                print(f"Erase failed at {hex(erase_addr)}: {e}")
                return_dict["status"] = False
                return_dict["msg"] = f"Erase error at 0x{erase_addr:08X}"
                return return_dict

        self.flash_write_disable()


        # Write loop
        print("Writing data pages...")
        write_addr = base_address
        self.flash_write_enable()
        for idx, hex_page in enumerate(self.bitstream):
            if write_addr >= max_address:
                print("Warning: Write exceeds assigned flash region.")
                break

            # hex to str
            page_bytes = bytes.fromhex(hex_page)
            page = list(page_bytes)

            if len(page) < FLASH_PAGE_SIZE:
                page += [0xFF] * (FLASH_PAGE_SIZE - len(page))  # Pad incomplete page

            print(f"Writing page {idx + 1}/{len(self.bitstream)} at 0x{write_addr:08X}")
            try:
                self.flash_write(write_addr, page)
                start = time.time()
                while self.flash_read_status() & 0x01:  # check flash status
                    if time.time() - start > FLASH_WIP_TIMEOUT_SEC:
                        raise TimeoutError("Flash busy > 10 s during writing")
                    time.sleep(FLASH_POLL_INTERVAL_SEC)
            except TimeoutError:
                return_dict["status"] = False
                return_dict["msg"] = "Flash stays busy for > 10 s, aborting"
                return return_dict
            except Exception as e:
                print(f"Write failed at {hex(write_addr)}: {e}")
                return_dict["status"] = False
                return_dict["msg"] = f"Write error at 0x{write_addr:08X}"
                return return_dict


            write_addr += FLASH_PAGE_SIZE  # Move to next 256-byte page

        self.flash_write_disable()
        return_dict["msg"] = "Successfully written to flash."
        return return_dict

        
    def read_from_flash(self, image_type: Literal["golden","operation"], save_to_file: bool = True):

        if image_type == "golden":
            base_address = FLASH_BASE_GOLDEN_BYTES
            max_address = FLASH_MAX_GOLDEN_BYTES
        elif image_type == "operation":
            base_address = FLASH_BASE_OPERATION_BYTES
            max_address = FLASH_MAX_OPERATION_BYTES
        else:
            return {"status": False, "msg": "Invalid image_type. Use 'golden' or 'operation'."}
        print("Reading flash pages...")

        read_addr = base_address
        pages = []

        while read_addr < max_address:
            try:
                page = self.flash_read(read_addr)
                pages.append(page)
                print(f"Read 256B page from 0x{read_addr:08X}, {page}") # print the address and data
            except Exception as e:
                print(f" Read failed at 0x{read_addr:08X}: {e}")
                return {"status": False, "msg": f"Read error at {hex(read_addr)}"}

            read_addr += FLASH_PAGE_SIZE

        # save in a new file
        if save_to_file:
            file_path = f"{image_type}_read_back.txt"
            try:
                with open(file_path, 'w') as f:
                    for page in pages:
                        hex_str = ''.join(f"{b:02x}" for b in page)
                        f.write(hex_str + "\n")
                print(f"Flash content saved to: {file_path}")
            except Exception as e:
                return {"status": False, "msg": f"Failed to save file: {str(e)}"}
            return {"status": True, "msg": f"Read {len(pages)} pages and saved to {file_path}", "data": pages}
        return {"status": True, "msg": f"Read {len(pages)}", "data": pages}





