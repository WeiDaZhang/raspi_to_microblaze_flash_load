"""
ModuleName               : PamirSerial
Software version number  : V1.1
Last Modified            : 09.10.2023
"""

"""
Documentation   : Please refer to "https://gitlab.physics.ox.ac.uk/weidazhang/pamir-raspi/-/tree/PaMIr_middleware" CommunicationProtocolSpecs.pdf
Description     : Middleware for basic read/write operation using registers in Microblaze.
Changes         : 
29.08.2023      : FIFO load and Read commands implemented.
09.10.2023      : __main__ function commented out and is implemented in new file.
"""

#
# *************************************Header strings definition****************************************
#
import sys
#import datetime
#import serial
import time
sys.path.insert(0, '/home/pi/Desktop/PamirSourceCode/Code/PamirSoftware/SourceCode/Common')
import Pamir_openConnection
from ast import literal_eval
#
# *************************************Command strings definition***************************************
#
reset_uart_str = '.Uart_Rst'
write_register_str = '.mm_WrReg'
write_ack_register_str = '.mm_WaReg'
read_register_str = '.mm_RdReg'
write_registers_str = '.mmWrRegs'
read_registers_str = '.mmRdRegs'
spi_write_register_str = '.SpiWrReg'
spi_read_register_str = '.SpiRdReg'
jesd_init_str = ".JesdInit"
flash_read_id_str = ".SpiFshRI\n"
flash_read_status_str = ".SpiFshRS\n" 
flash_read_flag_str = ".SpiFshRF\n"
flash_write_enable_str = ".SpiFshWE\n"
flash_write_disable_str = ".SpiFshWD\n"
flash_erase_str = ".SpiFshEr"
flash_read_256_str = ".SpiFshRd"
flash_write_256_str = ".SpiFshWr"
fifo_load_read_str = ".FifoLdRd"


reset_uart_ack_str = "Uart_Rst_ack\n"
jesd_init_ack_str = "JesdInit_ack\n"
flash_write_enable_ack_str = "SpiFshWE_ack\n"
flash_write_disable_ack_str = "SpiFshWD_ack\n"
flash_erase_ack_str = "SpiFshEr_ack\n"

iter_count = 1
iter_count_analysis = 2
iter_count_algo = 2
iter_count_time = 1



#
# *************************************Module PamirSerial start******************************************
#


class PamirSerial:
    def __init__(self, serialport = None, timeout = 1.0):
        #self.uart_device = uart_device
        self.ser = serialport
        self.uart_timeout = timeout
        self.debug = False

    def _read(self, nof_bytes):
        ret = self.ser.read(nof_bytes)
        if len(ret) < nof_bytes:
            raise Exception("Serial read timeout error")
            return None
        else:
            if self.debug:
                print("received:")
                print(ret)
            return ret.decode("utf-8")
    
    def _readline(self):
        ret = self.ser.readline()
        ret1 = self.ser.readline()
        if self.debug:
            print("received:")
            print(ret)
            print("received:")
            print(ret1)
            

    def _write(self, data):
        if self.debug:
            print("sending:")
            print(bytes(data, 'utf-8'))
        self.ser.write(bytes(data, 'utf-8'))

    def _flush(self):
        self.ser.timeout = 0.1
        while(len(self.ser.read(1))==1):
            pass
        self.ser.timeout = self.uart_timeout

    def _check_read_data(self, recv_str, address_present=True, data_length=8, data_num=1):
        if str(recv_str[len(recv_str)-1]) != '\n':
            raise Exception("Terminator not found in received string: " + recv_str)
            return False, None, None
            
        if address_present:
            if str(recv_str[0:2]) != "0x":
                raise Exception("0x not found in data in received string: " + recv_str)
                return False, None, None
            if str(recv_str[10]) != ' ':
                raise Exception("Space bwtween address and data not found in received string: " + recv_str)
                return False, None, None
            add = recv_str[0:10]
            add = int(add, 16)
            recv_str = recv_str[11:]
            
        if str(recv_str[0:2]) != "0x":
            raise Exception("0x not found in address in received string: " + recv_str)
            return False, None, None
        recv_str = recv_str[2:]
        
        data_list = []
        for k in range(data_num):
            data = recv_str[data_length*k : data_length*(k+1)]
            data = int(data, 16)
            data_list.append(data)
            
        if data_num == 1:
            data_list = data
            
        if address_present:
            return True, add, data_list
        else:
            return True, data_list
            
    def _hex_format(self, value, length=8):
        str = "0x"
        if type(value) == list:
            value_list = value
        else:
            value_list = [value]
        for val in value_list:
            if length == 8:
                str += f"{(val & 0xFFFFFFFF):08x}"
            elif length == 4: 
                str += f"{(val & 0xFFFF):04x}"
            else:
                str += f"{(val & 0xFF):02x}"
        return str
    #
    # Reset UART command
    #
    def reset_communication_bridge(self):
        b = reset_uart_str + '\n'
        self._write(b)
        self._flush()
        b = '\n'*(256+16) + reset_uart_str + '\n'
        self._write(b)
        time.sleep(0.5)
        data = self._read(13)
        if data != reset_uart_ack_str:
            raise Exception("Reset UART command error, ack not received correctly. Received: '%s'" % data)
            return False
        return True

    def jesd_init(self):
        b = jesd_init_str + '\n'
        self._write(b)
        data = self._read(13)
        if data != jesd_init_ack_str:
            raise Exception("JESD init command error, ack not received correctly. Received: '%s'" % data)
            return False
        return True
    #
    # Write Register commands
    #
    def register_write(self, address, data):
        b = write_register_str + " " + self._hex_format(address, 8) + " " + self._hex_format(data, 8) + '\n'
        self._write(b)
        #time.sleep(0.1)
        return True

    # Function to send a command and wait for an ACK
    def register_write_with_ack(self, address, data):
        retry_interval=0.1; 
        retry_interval=0.002; 
        max_retries=5
        retries = 0
        while retries < max_retries:
            response = "0x12345678 0x12345678\n"
            try:
                b = write_ack_register_str + " " + self._hex_format(address, 8) + " " + self._hex_format(data, 8) + '\n'
                #tstart1= time.time()
                self._write(b)
                #time.sleep(retry_interval)
                response =  self._read(22)  # Read the response    
                #tend1= time.time() 
                #print("send-receive time:-", tend1-tstart1)                 
            except Exception as e:
                print(f"Caught error: {e}")  
            success, read_add, read_data = self._check_read_data(response)
            if read_data == data and read_add == address:
                #time.sleep(0.1)
                return True  # ACK received, proceed
            else:
                print(f"Write data error, retrying... {response} ...{self._hex_format(address, 8)}...{self._hex_format(data, 8)}")
                time.sleep(retry_interval)
                retries += 1
        print("Max retries reached, proceeding without ACK.")
        #time.sleep(0.1)
        return False

    def register_write_with_readback(self, address, data):
        b = write_ack_register_str + " " + self._hex_format(address, 8) + " " + self._hex_format(data, 8) + '\n'
        for counter in range(0, iter_count): # To clear memory buffer ; Donot delete essential comment
            tstart1= time.time()
            self._write(b)
            #time.sleep(0.1)
            data = self._read(22)
            tend1= time.time() 
            print(f"time for write with read a single register is {tend1-tstart1} seconds")   
        success, read_add, read_data = self._check_read_data(data)
        #time.sleep(0.1)
        if not success:
            return None
        if read_add != address:
            raise Exception("Received address %s different from requested address %s: " % (hex(read_add, address)))
            return None
        else:
            return read_data
    #
    # Read Register commands
    #
    def register_read(self, address):
        b = read_register_str + " " + self._hex_format(address, 8) + '\n'
        for counter in range(0, iter_count): # To clear memory buffer ; Donot delete essential comment
            tstart1= time.time()
            self._write(b)
            data = self._read(22)
            tend1= time.time() 
            #print(f"time for reading a single register is {tend1-tstart1} seconds")   
        success, read_add, read_data = self._check_read_data(data)
        #time.sleep(0.1)
        if not success:
            return None
        if read_add != address:
            raise Exception("Received address %s different from requested address %s: " % (hex(read_add), hex(address)))
            return None
        return read_data
    
    def register_read_analysis(self, address):
        b = read_register_str + " " + self._hex_format(address, 8) + '\n'
        for counter in range(0, iter_count_analysis): # To clear memory buffer ; Donot delete essential comment
            self._write(b)
            data = self._read(22)
        success, read_add, read_data = self._check_read_data(data)
        #time.sleep(0.1)
        if not success:
            return None
        if read_add != address:
            raise Exception("Received address %s different from requested address %s: " % (hex(read_add), hex(address)))
            return None
        return read_data
    
    #
    # Read Register commands
    #
    def register_read_algo(self, address):
        b = read_register_str + " " + self._hex_format(address, 8) + '\n'
        for counter in range(0, iter_count_algo): # To clear memory buffer ; Donot delete essential comment
            self._write(b)
            data = self._read(22)
        success, read_add, read_data = self._check_read_data(data)
        #time.sleep(0.1)
        if not success:
            return None
        if read_add != address:
            raise Exception("Received address %s different from requested address %s: " % (hex(read_add), hex(address)))
            return None
        return read_data
    #
    # Read Register commands
    #
    def register_read_timekeep(self, address):
        b = read_register_str + " " + self._hex_format(address, 8) + '\n'
        for counter in range(0, iter_count_time): # To clear memory buffer ; Donot delete essential comment
            self._write(b)
            data = self._read(22)
        success, read_add, read_data = self._check_read_data(data)
        #time.sleep(0.1)
        if not success:
            return None
        if read_add != address:
            raise Exception("Received address %s different from requested address %s: " % (hex(read_add), hex(address)))
            return None
        return read_data
    #
    # Write/Read Burst accesses
    #
    def burst_register_write(self, nof_acc, start_address, data):
        count = nof_acc
        b = write_registers_str + " " + self._hex_format(nof_acc, 4) + " " + self._hex_format(start_address, 8)
        for element in data:
            b += " " + self._hex_format(element, 8)
        b += '\n'
        self._write(b)
        return True

    def burst_register_read(self, nof_acc, start_address):
        ret_list=[]
        b = read_registers_str + " " + self._hex_format(nof_acc, 4) + " " + self._hex_format(start_address, 8) + '\n'
        data = self._write(b)
        count = nof_acc
        for n in range(count):
            data = self._read(22)
            success, read_add, read_data = self._check_read_data(data)
            if not success:
                return None
            if read_add != start_address + 4*n:
                raise Exception("Received address %s different from requested address %s: " % (hex(read_add), hex(start_address + 4*n)))
                return None
            ret_list.append(read_data)
        return ret_list
    #
    # FIFO Load and Read commands
    #
    def fifo_load_read(self, address):
        b = fifo_load_read_str + " " + self._hex_format(address, 8) + '\n'
        self._write(b)
        data = self._read(2+8+1+2+256*2+1)
    #
    # SPI devices commands
    #
    def spi_register_write(self, index, address, data):
        b = spi_write_register_str + ' ' + self._hex_format(index, 4) + ' ' + self._hex_format(address, 8) + ' ' + self._hex_format(data, 8) + '\n'
        self._write(b)
        return True

    def spi_register_read(self, index, address):
        b = spi_read_register_str + ' ' + self._hex_format(index, 4) + ' ' + self._hex_format(address, 8) + '\n'
        self._write(b)
        data = self._read(22)
        success, read_add, read_data = self._check_read_data(data)
        if not success:
            return None
        if read_add != address:
            raise Exception("Received address %s different from requested address %s: " % (hex(read_add), hex(address)))
            return None
        return read_data
    #
    # QSPI FLASH commands
    #
    def flash_read_id(self):
        b = flash_read_id_str
        self._write(b)
        data = self._read(11)
        success, read_data = self._check_read_data(data, address_present=False)
        if not success:
            return None
        return read_data
        
    def flash_read_status(self):
        b = flash_read_status_str
        self._write(b)
        data = self._read(11)
        success, read_data = self._check_read_data(data, address_present=False)
        if not success:
            return None
        return read_data
        
    def flash_read_flag(self):
        b = flash_read_flag_str
        self._write(b)
        data = self._read(11)
        success, read_data = self._check_read_data(data, address_present=False)
        if not success:
            return None
        return read_data
        
    def flash_write_enable(self):
        b = flash_write_enable_str
        self._write(b)
        data = self._read(13)
        if data != flash_write_enable_ack_str:
            raise Exception("FLASH write enable command error, ack not received correctly. Received: '%s'" % data)
            return False
        return True
        
    def flash_write_disable(self):
        b = flash_write_disable_str
        self._write(b)
        data = self._read(13)
        if data != flash_write_disable_ack_str:
            raise Exception("FLASH write disable command error, ack not received correctly. Received: '%s'" % data)
            return False
        return True
        
    def flash_erase(self, address):
        b = flash_erase_str + ' ' + self._hex_format(address, 8) + '\n'
        self._write(b)
        data = self._read(13)
        if data != flash_erase_ack_str:
            raise Exception("FLASH Erase command error, ack not received correctly. Received: '%s'" % data)
            return False
        return True
       
    def flash_write(self, address, data):
        if len(data) != 256:
            raise Exception("FLASH Write command error, 256 element list expected, '%d' elements given." % len(data))
            return False
        b = flash_write_256_str + ' ' + self._hex_format(address, 8) + ' ' + self._hex_format(data, 2) + '\n'
        self._write(b)
        data = self._read(11)
        success, read_address = self._check_read_data(data, address_present=False)
        if read_address != address:
            raise Exception("FLASH Write command error, requested addrees is %s, received address is %s" % (hex(address), hex(read_address)))
            return False
        return True

    def flash_read(self, address):
        b = flash_read_256_str + ' ' + self._hex_format(address, 8) + '\n'
        self._write(b)
        data = self._read(2+8+1+2+256*2+1)
        success, read_address, data = self._check_read_data(data, address_present=True, data_length=2, data_num=256)
        if read_address != address:
            self._flush()
            raise Exception("FLASH Read command error, requested addrees is %s, received address is %s" % (hex(address), hex(read_address)))
            return None
        return data
#
# *************************************Module PamirSerial Ends********************************************
#
    # def SPI_read_flag_register_flash(self, index, address, data):
        # b = bytes('.spirfFsh\n', 'utf-8')
        # self._write(b)
        # ret, data = self._read(20)
        # return data

    # def SPI_write_protection_flash(self, index, address, data):
        # b = bytes('.spiwpFsh\n', 'utf-8')
        # self._write(b)
        # ret, data = self._read(9)
        # return data

    # def daq_status_multiread(self, nof_acc, start_address):
        # ret_list=[]
        # b = bytes('.mmRdRegs' + " " + nof_acc + " " + start_address + '\n', 'utf-8')
        # data = self._write(b)
        # count = int(nof_acc, 16)
        # for n in range(1, count+1):
            # ret, data = self._read(22)
            # ret_list.append(data)
        # return ret_list

    # def daq_engine_state_control(self, address, data):
        # b = bytes('.mm_waReg' + " " + address + " " + data + '\n', 'utf-8')
        # self._write(b)
        # ret, data = self._read(22)
        # return data

    # def daq_multiple_register_write(self, number_of_access, start_address, data):
        # count = literal_eval(number_of_access)
        # b = bytes('.mm_wrReg' + " " + number_of_access + " " + start_address + " ", 'utf-8')
        # for element in data:
            # b += bytes(element + " ", 'utf-8')
        # b += bytes('\n', 'utf-8')
        # self._write(b)
        # return True



"""
**************************************** Main Module Start ********************************************************
__name__ == "__main__" ; Used till 09.10.2023
"""
"""
if __name__ == "__main__":

    from optparse import OptionParser
    from sys import argv, stdout

    parser = OptionParser(usage="usage: %station [options]")
    parser.add_option("-d", "--device", action="store", dest="uart_device",
                      #default='/dev/ttyUSB6', help="UART device [default: /dev/ttyUSB6]")
                      default='/dev/ttyS0', help="UART device [default: /dev/ttyS0]")
    (conf, args) = parser.parse_args(argv[1:])
    print(conf)
    pamir_serial = PamirSerial(uart_device=conf.uart_device,
                               speed=230400,
                               timeout=10.0)

    print("Starting tests...")
    print("Turning DEBUG on...")
    pamir_serial.debug = True

    print("Executing reset_communication_bridge command...")
    ret = pamir_serial.reset_communication_bridge()
    if ret:
        print("success.\n")
    else:
        print("fail.\n")

    print("Executing JESD init command...")
    ret = pamir_serial.jesd_init()
    if ret:
        print("success.\n")
    else:
        print("fail.\n")

    print("Send Load and Read FIFO commands...")
    add = 0x44A40000
    pamir_serial.fifo_load_read(add)

    print("Executing single write and read register commands...")
    add = 0x44A50000
    data = 0x12345678
    pamir_serial.register_write(add, data)
    read_data = pamir_serial.register_read(add)
    if read_data == data:
        print("success.\n")
    else:
        print("fail.\n")

    print("Executing single write with readback commands...")
    add = 0x44A50000
    data = 0x11223344
    read_data = pamir_serial.register_write_with_readback(add, data)
    if read_data == data:
        print("success.\n")
    else:
        print("fail.\n")

    print("Executing burst write and read register commands...")
    add = 0x44A50000
    num = 4 
    data = [0x1111, 0x2222, 0x3333, 0x4444]
    pamir_serial.burst_register_write(num, add, data)
    read_data = pamir_serial.burst_register_read(num, add)
    if read_data == data:
        print("success.\n")
    else:
        print("fail.\n")

    print("Executing SPI read register command, reading VENDOR_ID register in AD9528 PLL...")
    read_data = pamir_serial.spi_register_read(1, 0xC)
    if read_data == 0x56:
        print("success.\n")
    else:
        print("fail.\n")

    print("Executing SPI write read register commands on AD9680 scratchpad register 0xA...")
    pamir_serial.spi_register_write(2, 0xA, 0xa5)
    read_data = pamir_serial.spi_register_read(2, 0xA)
    if read_data == 0xa5:
        print("success.\n")
    else:
        print("fail.\n")
        
    print("Executing QSPI FLASH Read ID command...")
    read_data = pamir_serial.flash_read_id()
    if read_data == 0xBB1910:
        print("success.\n")
    else:
        print("fail.\n")
        
    print("Executing QSPI FLASH Read Status command...")
    read_data = pamir_serial.flash_read_status()
    if read_data == 0x0:
        print("success.\n")
    else:
        print("fail.\n")
        
    print("Executing QSPI FLASH Read Flag register command...")
    read_data = pamir_serial.flash_read_flag()
    if read_data == 0x80:
        print("success.\n")
    else:
        print("fail.\n")
            
    print("Executing QSPI FLASH Write Enable command...")
    if pamir_serial.flash_write_enable():
        print("success.\n")
    else:
        print("fail.\n")
        
    print("Executing QSPI FLASH Write Disable command...")
    if pamir_serial.flash_write_disable():
        print("success.\n")
    else:
        print("fail.\n")
        
    print("Executing QSPI FLASH Erase sector command...")
    if pamir_serial.flash_erase(1):
        print("success.\n")
    else:
        print("fail.\n")
        
    print("Executing QSPI FLASH Write command...")
    if pamir_serial.flash_write(1, list(range(256))):
        print("success.\n")
    else:
        print("fail.\n")
        
    print("Executing QSPI FLASH Read command...")
    if pamir_serial.flash_read(1) == list(range(256)):
        print("success.\n")
    else:
        print("fail.\n")
    
    print("Turning DEBUG off...")
    pamir_serial.debug = False
    print("Tests finished!")
"""
"""
**************************************** Main Module End ********************************************************
"""

    # try:
    
        # Erase flash
        # address = "0x12345678"
        # ret_data = pamir_serial.flash_erase(address)
        # print(ret_data)
        
        # Write flash page of 256Bdata
        # address = "0x76543210"
        # data_to_send = "256 bytes data to send"
        # ret_data = pamir_serial.flash_write(address, data_to_send)
        # print(ret_data)
        
        # Read Flash
        # address = "0x12345678"
        # ret_data = pamir_serial.flash_read(address)
        # print(ret_data)
    
    
    
        # Reset the UART communication bridge on FPGA. Returns "Rst_success" if successful
        # data1 = pamir_serial.reset_communication_bridge()
        # print(data1)

        # This mode queris the DAQ firmware on FPGA to read all status register info# Returns a list of all received status info
        # Equivalent to multiple register read
        # number_of_access = "0x0004"
        # start_address = "0x00000001"
        # ret_data_list = pamir_serial.daq_status_multiread(number_of_access,start_address)
        # print(ret_data_list)
        
        # DAQ engine state control : Returns an echo of Tx word being send
        # address = "0x00010000"
        # data_to_send = "0x11110000"
        # ret_data = pamir_serial.daq_engine_state_control(start_address,data_to_send)
        # print(ret_data)
        
        # Single Register read- to read a register at address specified; returns address + data
        # address = "0x00010000"
        # data_to_send = "0x00000000"
        # ret_data = pamir_serial.single_register_read(start_address,data_to_send)
        # print(ret_data)
        
        # Writes a register at address specified; returns true
        # address = "0x00010000"
        # data_to_send = "0x11110000"
        # ret_data = pamir_serial.single_register_write(start_address,data_to_send)
        # print(ret_data)
        
        # writes a register and read its value to confirm; returns data that is send if successful
        # start_address = "0x00010000"
        # data_to_send = "0x11110000"
        # ret_data = pamir_serial.single_register_write_with_readback(start_address,data_to_send)
        # print(ret_data)
        
        # multiple consecutive registers are getting writtern here
        # number_of_registers = "0x0004"
        # start_address = "0x00000001"
        # data_to_send = ["0x00020000","0x00030000","0x00040000","0x000F0000"]
        # pamir_serial.daq_multiple_register_write(number_of_registers,start_address, data_to_send)
        # print(ret_data)
        

        

        

                
    # except KeyboardInterrupt:
        # pamir_serial.close()