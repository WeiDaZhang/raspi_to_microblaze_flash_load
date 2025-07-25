import time
import os
import sys
import serial
import logging
from typing import Literal

from serial_commport.Pamir_serial_basic import PamirSerial

# It turns out "flash_erase", "flash_write", "flash_read" has been provided by [Meenu S]
# You would want to override them and potentially encapsulate them
FLASH_PAGE_SIZE = 256  # bytes  per program-page
FLASH_SECTOR_SIZE = 0x10000  # 64 KiB per sector
FLASH_ADDRBASE_GOLDEN = 0x00000000
FLASH_ADDRBASE_OPERATION = 0x01000000
IMAGE_MAX_SIZE_BYTES = FLASH_ADDRBASE_OPERATION
FLASH_WIP_TIMEOUT_SEC = 10.0
FLASH_POLL_INTERVAL_SEC = 0.05
FPGA_BITSTREAM_SYNC_WORD = (
    "AA995566"  # 4 bytes sync word at the start of the bitstream file
)
FPGA_BITSTREAM_IDCODE = {
    "XCKU040": "3822093"  # Expected IDCODE for the FPGA
}
ALLOW_EXTS = [".bin"]


class FlashLoad(PamirSerial):
    @staticmethod
    def read_binary_to_hex(filename, max_bytes=FLASH_PAGE_SIZE) -> dict:
        return_dict = {"status": True, "msg": None}
        hex_pages: list[str] = []
        bin_pages: list[bytes] = []
        try:
            with open(filename, "rb") as f:
                while True:
                    data = f.read(max_bytes)
                    if not data:
                        break
                    bin_pages.append(data)
                    hex_pages.append(data.hex())
                return_dict["data"] = hex_pages
                return_dict["bin_data"] = bin_pages
                return return_dict
        except FileNotFoundError:
            return_dict["status"] = False
            return_dict["msg"] = "Error: File not found"
        except Exception as e:
            return_dict["status"] = False
            return_dict["msg"] = f"Error: {str(e)}"
        return return_dict

    def load_bitstream_file(self, file_name: str, fpga_type="XCKU040") -> dict:
        if fpga_type not in FPGA_BITSTREAM_IDCODE:
            return {
                "status": False,
                "msg": f"Unsupported FPGA type: {fpga_type}. Supported types: {', '.join(FPGA_BITSTREAM_IDCODE.keys())}",
            }
        # check if extension provided in the file name
        if "." not in file_name:
            return {"status": False, "msg": "No file extension provided."}
        _, ext = os.path.splitext(file_name)
        # check if correct extensions
        if ext.lower() not in ALLOW_EXTS:
            return {
                "status": False,
                "msg": f"Unsupported file extension: {ext}. Allowed extensions: {', '.join(ALLOW_EXTS)}",
            }

        if not os.path.isfile(file_name):
            return {"status": False, "msg": "Error: File not found."}

        # check size of the file
        file_size = os.path.getsize(file_name)
        if file_size > IMAGE_MAX_SIZE_BYTES:
            return {
                "status": False,
                "msg": f"Error: File too large ({file_size} bytes). Max allowed is {IMAGE_MAX_SIZE_BYTES} bytes.",
            }
        print(f"Size of the file：{file_size} bytes")

        return_dict = self.read_binary_to_hex(file_name)
        if not return_dict["status"]:
            return return_dict
        else:
            # check syncronisation code "AA995566" exists, etc.,
            whole_file_string = "".join(return_dict["data"])
            if whole_file_string.lower().find(FPGA_BITSTREAM_SYNC_WORD.lower()) == -1:
                return {
                    "status": False,
                    "msg": f"Missing synchronisation code {FPGA_BITSTREAM_SYNC_WORD}.",
                }

            if (
                whole_file_string.lower().find(FPGA_BITSTREAM_IDCODE[fpga_type].lower())
                == -1
            ):
                return {
                    "status": False,
                    "msg": f"Missing synchronisation code {FPGA_BITSTREAM_SYNC_WORD}.",
                }
            self.bitstream: list[bytes] = return_dict["bin_data"]
            return return_dict

    def write_image_to_flash(
        self, image_type: Literal["golden", "operation"] = "operation"
    ):
        return_dict = {"status": True, "msg": None}
        if not hasattr(self, "bitstream"):
            return_dict["status"] = False
            return_dict["msg"] = "Valid bitstream is not loaded."
            return return_dict

        # check image_type
        if image_type == "golden":
            base_address = FLASH_ADDRBASE_GOLDEN
            max_address = FLASH_ADDRBASE_GOLDEN + IMAGE_MAX_SIZE_BYTES - 1
        elif image_type == "operation":
            base_address = FLASH_ADDRBASE_OPERATION
            max_address = FLASH_ADDRBASE_OPERATION + IMAGE_MAX_SIZE_BYTES - 1
        else:
            return_dict["status"] = False
            return_dict["msg"] = "Invalid image_type. Use 'golden' or 'operation'."
            return return_dict

        # Erase loop
        print("Erasing sectors...")

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

        # Write loop
        print("Writing data pages...")
        write_addr = base_address
        for idx, bin_page in enumerate(self.bitstream):
            if write_addr >= max_address:
                print("Warning: Write exceeds assigned flash region.")
                break

            bin_page_list = list(bin_page)

            if len(bin_page_list) < FLASH_PAGE_SIZE:
                bin_page_list += [0xFF] * (
                    FLASH_PAGE_SIZE - len(bin_page_list)
                )  # Pad incomplete page

            print(f"Writing page {idx + 1}/{len(self.bitstream)} at 0x{write_addr:08X}")
            try:
                self.flash_write(write_addr, bin_page_list)
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

    def read_image_from_flash(
        self, image_type: Literal["golden", "operation"], save_to_file: bool = False
    ):
        if image_type == "golden":
            base_address = FLASH_ADDRBASE_GOLDEN
            max_address = FLASH_ADDRBASE_GOLDEN + IMAGE_MAX_SIZE_BYTES - 1
        elif image_type == "operation":
            base_address = FLASH_ADDRBASE_OPERATION
            max_address = FLASH_ADDRBASE_OPERATION + IMAGE_MAX_SIZE_BYTES - 1
        else:
            return {
                "status": False,
                "msg": "Invalid image_type. Use 'golden' or 'operation'.",
            }
        print("Reading flash pages...")

        read_addr = base_address
        list_byte: list[int] = []

        while read_addr < max_address:
            try:
                page = self.flash_read(read_addr)
                list_byte.extend(page)
                str_hex_page = "".join(f"{b:02x}" for b in page)
                print(
                    f"Read 256B page from 0x{read_addr:08X}, 0x{str_hex_page}"
                )  # print the address and data
            except Exception as e:
                print(f" Read failed at 0x{read_addr:08X}: {e}")
                return {"status": False, "msg": f"Read error at {hex(read_addr)}"}

            read_addr += FLASH_PAGE_SIZE

        # save in a new file
        if save_to_file:
            file_path = f"{image_type}_read_back.txt"
            try:
                with open(file_path, "w") as f:
                    for page in list_byte:
                        hex_str = "".join(f"{b:02x}" for b in page)
                        f.write(hex_str + "\n")
                print(f"Flash content saved to: {file_path}")
            except Exception as e:
                return {"status": False, "msg": f"Failed to save file: {str(e)}"}
            return {
                "status": True,
                "msg": f"Read {len(list_byte)} pages and saved to {file_path}",
                "data": list_byte,
            }
        return {
            "status": True,
            "msg": f"Read {len(list_byte)} bytes",
            "data": list_byte,
        }
