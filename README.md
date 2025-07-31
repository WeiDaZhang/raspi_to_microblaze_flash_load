# FlashLoad Utility

This repository provides a Python utility to manage flash memory operations
for FPGA bitstream files. The core class, `FlashLoad`, implements non-blocking
read and write operations to flash memory over a serial interface, with support
for pausing, resuming, aborting, and progress monitoring.

## Features

- **Non-blocking operations:** Uses threads and events to perform flash read/write
  operations without blocking the main application.
- **Bitstream file validation:** Checks file size, extension, sync word (`AA995566`),
  and FPGA ID code (e.g., `3822093` for XCKU040) before performing any operation.
- **Erase and Write:** Automatically erases required flash sectors before writing
  the bitstream, with progress feedback and error handling.
- **Read-back support:** Enables reading flash memory in pages for verification.
- **Operation Control:** Supports commands to pause, resume, or abort an ongoing
  flash operation.

## Requirements

- Python 3.8+
- [pyserial](https://pypi.org/project/pyserial/)
- `serialcommport.Pamir_serial_basic.PamirSerial` (custom dependency)

## File Structure

- `flash_load.py`  
  Contains the `FlashLoad` class with its flash programming, erasing, and read-back
  functionality.

- `test_scripts/non_blocking_flash_load_test.py`  
  An interactive command-line test script demonstrating how to use the `FlashLoad`
  class. This script supports operations like:
  
  - **load**: Load a bitstream file and validate its content.
  - **write**: Start the flash write operation.
  - **read**: Start the flash read operation.
  - **prog**: Check and display the progress/status of an ongoing flash operation.
  - **pause**: Pause the current flash operation.
  - **resume**: Resume a paused operation.
  - **abort**: Abort the ongoing operation.
  - **quit/exit**: End the test session.

## Usage

1. **initialization**

    ```
    fl = FlashLoad(serialport=None, timeout=1.0)
    ```
    a prepared serial port for FPGA mother board communication

2. **Load bitstream**

    ```
    fl.load_bitstream_file(file_name: str, fpga_type="XCKU040") -> dict
    ```
    Function load_bitstream_file must be called before write image operation or non-blocking write operation.
    A file_name must be prepared and provided as a string which points to a ".bin" file address.
    The argument fpga_type should not be altered unless special situation, using the default value (meaning do not provided this argument when calling is suggested)

3. **Blocking read and write**
    ```
    fl.write_image_to_flash(
        image_type: Literal["golden", "operation"] = "operation",
    ) -> dict
    fl.read_image_from_flash(
        image_type: Literal["golden", "operation"],
        length: int = 0,  # Length in bytes, 0 means maximum image size
    ) -> dict
    ```
    These two functions are blocking call for write and read operation, which will not return until finished or failed.
    Calling the non-blocking functions below is preferred.

4. **Initialize non-blocking flash operation**
    ```
    fl.init_flash_operation(
        image_type: Literal["golden", "operation"],
        operation_type: Literal["write", "read"],
        read_length: int = 0,  # Length in bytes for read operation, ignored in write operation
    )
    ```
    Two image_type (s) are accepted, provide with string "golden" or "operation".
    Two operation_type (s) are accepted, provide with string "write" or "read".
    When operation_type is "read", read_length could be provided to limit the length of reading, integer value should be provided in unit of [Byte], if 0 is provided, full possible image size is read.
    If operation_type is "write", read_length is ignored.
    When read_length is not integer multiple of flash page size, read operation will round up to integer multiple of flash page size (256 byte).

    **BE VERY CAREFUL WHEN TRYING TO WRITE TO GOLDEN IMAGE**

5. **Checking status of non-blocking flash operation**
    ```
    fl.flash_operation_status(
        status_check_timeout: float = 0.5,
    ) -> list[dict]:
    ```
    Call this function to obtain status of the ongoing flash operation.
    Return value is a list of dictionaries, each dictionary is a previous status.
    The dictionary is in following format:
    ```
    {"status": bool, "msg": str, (optional "data": list[int])}
    ```
    When preceding flash operation is ongoing without error, value of the "status" key is True.
    If the preceding flash operation is ended, aborted by user or error occured, value of the "status" key is False.
    If the preceding flash operation is of the type "read", the read result will be embedded in the last status return as the value of "data" key, the type of value is list of integer, each of which is a byte read from the flash.

6. **Set flash operation pause, resume and abort**
    ```
    fl.set_flash_operation_pause()
    fl.set_flash_operation_resume()
    fl.set_flash_operation_abort()
    ```
    As the function names suggested, only apply to non-blocking flash operations.
