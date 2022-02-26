# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2020, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        serial_port.py
# @Author:      philosophy
# @Created:     2021/5/1 - 23:34
# --------------------------------------------------------
import os
import copy
import chardet
import serial
import serial.tools.list_ports as list_ports
from concurrent.futures.thread import ThreadPoolExecutor
from time import sleep
from typing import Union, Optional

import autotest.utils.utils as utils
from ..logger import logger
from ..checker import check_connect, connect_tips


class SerialPort(object):
    """
    串口类，用于基础的串口操作
    """

    def __init__(self):
        self._serial = None
        # 端口号，用于写文件
        self._port = None
        # 文件写入循环
        self._flag = False
        # 线程池句柄
        self._thread_pool = ThreadPoolExecutor(max_workers=1)
        # 读取的数据来源标识符，当False的时候表示从缓存中读取，此时没有写入文件， True的时候则从contents中读取，表示写入了文件
        self._read_flag = False
        # 读到的数据
        self._contents = []

    @staticmethod
    def __detect_codec(string: bytes):
        """
        检测编码类型并返回

        :param string:输入的未解码的字符串

        :return  返回编码类型
        """
        encode = chardet.detect(string)
        logger.trace(f"codec is {encode['encoding']}")
        encoding = encode['encoding']
        return encoding if encoding else "utf-8"

    def __bytes_to_string(self, line: bytes, type_: Optional[bool] = None) -> str:
        """
        获取一行数据

        :param line: 一行的数据

        :param type_: 类型

        :return 行数据
        """
        if type_:
            return line if type_ else line.decode("utf-8")
        else:
            return line.decode(self.__detect_codec(line))

    def __read_line(self, type_: Optional[bool] = None) -> str:
        """
        读取串口输出，按行读取，调用一次读取一行

        :param type_:

            True:不进行解码操作，直接返回

            False:以utf-8的方式进行解码并返回

            None: 自动检测编码格式，并自动解码后返回

        :return: 读取到的串口输出string
        """
        line = self._serial.readline()
        return self.__bytes_to_string(line, type_)

    def __write_log_file(self, log_folder: str):
        """
        log_folder，传入文件夹

        :param log_folder: 文件或者文件夹
        """
        self._flag = True
        file_fmt = "%Y%m%d_%H%M%S"
        content_fmt = "%Y/%m/%d %H:%M:%S"
        parent = log_folder.split("\"")[0]
        if os.path.exists(log_folder):
            if os.path.isdir(log_folder):
                log_file = fr"{log_folder}\{self._port}_{utils.get_time_as_string(fmt=file_fmt)}.log"
            else:
                log_file = fr"{parent}\{self._port}_{utils.get_time_as_string(fmt=file_fmt)}.log"
        else:
            if os.path.exists(parent):
                log_file = f"{self._port}_{utils.get_time_as_string(fmt=file_fmt)}.log"
            else:
                raise RuntimeError(f"{log_folder} is not exist, please check it")
        self._read_flag = True
        with open(log_file, "a+", encoding="utf-8") as f:
            count = 1
            while self._flag:
                current_time = utils.get_time_as_string(fmt=content_fmt)
                content = self.__read_line()
                if content != "":
                    content = content.replace("\r\n", "").replace("\r", "")
                    self._contents.append(content)
                    line = f"[{current_time}] {content} \r"
                    logger.debug(f"line = {line}")
                    f.write(line)
                # 100行内容写入一次
                if count % 100 == 0:
                    logger.debug("flush to file")
                    f.flush()
                count += 1
            f.flush()

    def connect(self,
                port: str,
                baud_rate: int,
                byte_size: int = serial.EIGHTBITS,
                parity: str = serial.PARITY_NONE,
                stop_bits: int = serial.STOPBITS_ONE,
                xon_xoff: bool = False,
                rts_cts: bool = False,
                dsr_dtr: bool = False,
                timeout: float = 0.5,
                write_timeout: float = 3,
                log_folder: Optional[str] = None):
        """
        创建新的串口会话窗口、

        :param log_folder: 记录日志的log

        :param port: 串口端口：COM1， 必填

        :param baud_rate: 波特率必填
            (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,9600, 19200, 38400, 57600, 115200, 230400,
            460800, 500000, 576000, 921600, 1000000, 1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000)

        :param byte_size:
            #数据位： (FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS)， 默认=EIGHTBITS

        :param parity:
            #奇偶校验位： (PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE)，默认=PARITY_NONE

        :param stop_bits:
            #停止位： one of (STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO)，默认=STOPBITS_ONE

        :param xon_xoff: #XONXOFF

        :param rts_cts: #RTSCTS

        :param dsr_dtr: #DTRDSR

        :param timeout: # 读取数据超时设置，必须设置，否则会block forever， 默认=0.5

        :param write_timeout: # 写入数据超时设置
        """
        if self.check_port(port):
            self._serial = serial.Serial(port=port, baudrate=baud_rate, bytesize=byte_size, parity=parity,
                                         stopbits=stop_bits, timeout=timeout, xonxoff=xon_xoff, rtscts=rts_cts,
                                         write_timeout=write_timeout, dsrdtr=dsr_dtr)
            # self._serial.open()
            # self.set_buffer()
        else:
            raise RuntimeError(f"port[{port}] connect failed")
        sleep(1)
        self._port = port
        if log_folder:
            self._thread_pool.submit(self.__write_log_file, log_folder)

    def disconnect(self):
        """
        关闭串口
        """
        if self._serial:
            self._flag = False
            self._port = None
            self._read_flag = False
            self._serial.close()
            self._serial = None
            # 清除数据
            self._contents.clear()

    @staticmethod
    def check_port(port: str) -> bool:
        """
        检测已连接的串口端口

        :param port: 用于连接串口的端口，检测该端口是否可用

        :return:
            True: 已连接

            False: 未连接
        """
        ports = {}
        for port_obj in list_ports.comports():
            ports[port_obj.device] = port_obj.description
        if port.upper() in ports.keys():
            return True
        logger.warning(f"un support COM port: {port}, should be one of :{ports}")
        return False

    @check_connect("_serial", connect_tips, True)
    def send(self, cmd: Union[bytes, str], type_: bool = True, end: str = '\r'):
        """
        发送命令到串口

        :param cmd: 发送的串口命令

        :param type_: 编码方式

            True: bytes模式

            False: string模式

        :param end:是否增加结束符，默认为为\r
        """
        if isinstance(cmd, str):
            cmd = cmd + end if end else cmd
        if type_:
            if not isinstance(cmd, bytes):
                cmd = cmd.encode("utf-8")
        self._serial.write(cmd)

    @check_connect("_serial", connect_tips, True)
    def send_break(self):
        """
        发送终止命令，停止打印
        """
        self._serial.sendBreak(duration=0.25)

    @check_connect("_serial", connect_tips, True)
    def read_bytes(self, byte_number: Optional[int] = None, type_: Optional[bool] = None) -> bytes:
        """
        读取串口输出，按byte读取

        :param byte_number: 读取的字节数，不写则默认1

        :param type_:

            True:不进行解码操作，直接返回

            False:以utf-8的方式进行解码并返回

            None: 自动检测编码格式，并自动解码后返回

        :return: 读取到的串口输出bytes
        """
        byte_ = self._serial.read(byte_number) if byte_number is not None else self._serial.read()
        if type_ is None:
            return byte_.decode(self.__detect_codec(byte_))
        else:
            return byte_.decode('utf-8') if type_ else byte_

    @check_connect("_serial", connect_tips, True)
    def read_line(self) -> str:
        """
        读取串口输出，按行读取，调用一次读取一行


        :return: 读取到的串口输出string
        """
        if self._read_flag:
            if len(self._contents) > 0:
                # content = self._contents[0]
                content = self._contents.pop(0)
                return content
            else:
                return ""
        else:
            return self.__read_line()

    @check_connect("_serial", connect_tips, True)
    def read_lines(self, type_: Optional[bool] = None) -> list:
        """
        读取串口输出，读取所有行，返回列表

        :param type_:

            True:不进行解码操作，直接返回

            False:以utf-8的方式进行解码并返回

            None: 自动检测编码格式，并自动解码后返回

        :return: 读取到的串口输出list
        """
        if self._read_flag:
            contents = copy.deepcopy(self._contents)
            self._contents.clear()
            return contents
        else:
            lines = self._serial.readlines()
            result = []
            for line in lines:
                result.append(self.__bytes_to_string(line, type_))
            return result

    @check_connect("_serial", connect_tips, True)
    def read_all(self, type_: Optional[bool] = None) -> str:
        """
        读取串口输出，一次性把所有输出读取

        :param type_:

            True:不进行解码操作，直接返回

            False:以utf-8的方式进行解码并返回

            None: 自动检测编码格式，并自动解码后返回

        :return: 读取到的串口输出string
        """
        if self._read_flag:
            logger.debug(f"file mode, self._contents length = {len(self._contents)}")
            contents = copy.deepcopy(self._contents)
            logger.debug(f"contents length = {len(contents)}")
            self._contents.clear()
            return " ".join(contents)
        else:
            logger.info(f"serial mode")
            all_lines = self._serial.read_all()
            sleep(2)
            return self.__bytes_to_string(all_lines, type_)

    @check_connect("_serial", connect_tips, True)
    def in_waiting(self) -> int:
        """
        获取接收缓存区数据大小

        :return: 接收缓存区数据字节数:int
        """
        return self._serial.in_waiting

    @check_connect("_serial", connect_tips, True)
    def out_waiting(self) -> int:
        """
        获取写命令缓存区数据大小

        :return: 写命令缓存区数据字节数:int
        """
        return self._serial.out_waiting

    @check_connect("_serial", connect_tips, True)
    def flush(self):
        """
        清空所有缓存
        """
        self._serial.flush()

    @check_connect("_serial", connect_tips, True)
    def flush_all(self):
        """
        同时清空input和output
        """
        self.flush_output()
        self.flush_input()

    @check_connect("_serial", connect_tips, True)
    def flush_input(self):
        """
        清空输入缓存
        """
        self._serial.flushInput()

    @check_connect("_serial", connect_tips, True)
    def flush_output(self):
        """
        清空输出缓存
        """
        self._serial.flushOutput()

    @check_connect("_serial", connect_tips, True)
    def reset_input_buffer(self):
        """
        清除串口输入缓存
        """
        self._serial.reset_input_buffer()

    @check_connect("_serial", connect_tips, True)
    def reset_output_buffer(self):
        """
        清除串口输出缓存
        """
        self._serial.reset_output_buffer()

    @check_connect("_serial", connect_tips, True)
    def set_buffer(self, rx_size: int = 16384, tx_size: int = 16384):
        """
        设置串口缓存大小，默认4096

        :param rx_size: 接收缓存区大小设置

        :param tx_size: 发送缓存区大小设置
        """
        self._serial.set_buffer_size(rx_size, tx_size)
