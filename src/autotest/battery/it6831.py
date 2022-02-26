# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2020, lizhe, All rights reserved
# --------------------------------------------------------
# @Name:        it6831.py
# @Author:      lizhe
# @Created:     2021/5/1 - 23:59
# --------------------------------------------------------
from time import sleep

from ..utils.serial_utils import serial_port
from ..checker import check_connect, battery_tips
from ..logger import logger


class Status(object):

    def __init__(self):
        self.current = 0
        self.voltage = 0
        self.power = 0
        self.over_hot = 0
        self.remote = 0
        self.output_mode = None
        self.fan_level = 0
        self.max_voltage = 18.0
        self.set_current = 0
        self.set_voltage = 0
        self.available_flag = False


class IT6831(object):
    """
    用于通过串口控制IT6831可编程电源，需要接上串口转TTL。

    说明：

      目前IT6831支持电源电压最大18V，电流最大20A，调节的时候不要超过该设定电压，否则会调节失败。

    操作步骤：

    """

    def __init__(self, port: str, baud_rate: int = 9600):
        self.__serial = serial_port
        self.__port = port
        self.__baud_rate = baud_rate
        self.__address = '00'
        self.__max_voltage = 18.000
        self.__max_current = 10.000
        self.__connected = False

    def __get_frame(self, length: int = 26, init_value: int = '00') -> str:
        """
        获取一个原始的帧，所有数据初始为0

        :param length: 数据总长度，按字节

        :param init_value: 数据的初始状态

        :return: 长度为26个字节的16进制字符串
        """
        logger.debug(f"address = [{self.__address}]")
        return "AA" + self.__address + str(init_value) * int(length - 2)

    @staticmethod
    def __set_frame(start: int, length: int, data: str, frame: str) -> str:
        """
        修改帧数据

        :param start: 修改帧的起始位置，从1开始

        :param length: 修改帧中的数据长度

        :param data:  要应用的修改数据

        :param frame: 要修改的帧数据

        :return: 返回修改之后的帧数据，字符串类型
        """
        start -= 1
        new_frame = list(frame)
        end = start + length - 1
        if start < 0 or start >= len(new_frame) or end >= len(new_frame):
            raise ValueError("param 'start' or 'length' error.")
        if length != len(data):
            raise ValueError("length of 'data' not equal to 'length'.")
        count = 0
        for i in range(start, start + length):
            new_frame[i] = data[count]
            count += 1
        return ''.join(new_frame)

    def __send(self, input_frame: str):
        """
        调用串口接口发送帧数据

        :param input_frame:  要发送的帧数据，字符串

        :return: 返回串口发送后的返回值
        """
        byte_value = bytes.fromhex(input_frame)
        self.__serial.send(byte_value, False, end="")

    def __get_check_sum(self, input_frame: str, start: int = 51, length: int = 2) -> str:
        """
        求校验和，校验码

        :param input_frame: 需要计算校验码的输入帧数据

        :param start:  修改帧的起始位置

        :param length: 修改帧中的数据长度

        :return: 返回填入校验码之后的帧数据，字符串类型
        """
        sum_ = 0
        for i in range(0, len(input_frame) - 2, 2):
            tmp = input_frame[i:i + 2]
            data_hex = bytes.fromhex(tmp).hex()
            data_int = int(data_hex, 16)
            sum_ += data_int
        sum_ = hex(sum_ % 256)
        if len(sum_) == 3:
            sum_ = sum_[:2] + '0' + sum_[2:]
        return self.__set_frame(start, length, sum_[2:], input_frame)

    def open(self):
        """
        打开并连接IT6831电源
        """
        self.__serial.connect(port=self.__port, baud_rate=self.__baud_rate)
        if self.get_all_status().available_flag:
            self.__connected = True

    def close(self):
        """
        关闭串口，必须在任务结束后调用，否则串口会阻塞，需要重新插拔一下
        """
        self.__serial.disconnect()
        self.__connected = False

    @check_connect("__connected", battery_tips)
    def set_power_control_mode(self, switch: bool = True):
        """
        设置控制电源的操作模式

        :param switch:
            True 远程操控模式

            False 面板操作模式
        """
        if switch:
            mode = "01"
        else:
            mode = "00"
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '20', frame)
        frame = self.__set_frame(4 * 2 - 1, 2, mode, frame)
        frame = self.__get_check_sum(frame)
        logger.debug(f"set power control mode frame: {frame}")
        self.__send(frame)

    @check_connect("__connected", battery_tips)
    def set_power_output_status(self, switch: bool = True):
        """
        设置控制电源输出状态

        :param switch:
            True ON

            False OFF
        """
        if switch:
            mode = "01"
        else:
            mode = "00"
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '21', frame)
        frame = self.__set_frame(4 * 2 - 1, 2, mode, frame)
        frame = self.__get_check_sum(frame)
        logger.debug(f"set power output status frame: {frame}")
        self.__send(frame)

    @check_connect("__connected", battery_tips)
    def set_voltage_limit(self, limit: float = 18.000):
        """
        设置电源的电压上限

        :param limit: 电源的电压上限,必须介于0-18.000之间，数据类型为float
        """
        if limit <= 0 or limit > 18.000:
            logger.error("voltage limit must be [0, 18.000], set to 18.000.")
            limit = 18.000
        limit = int(limit * 1000)
        limit_hex = hex(limit)[2:]
        limit_hex = '0000000' + limit_hex
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '22', frame)
        frame = self.__set_frame(4 * 2 - 1, 2, limit_hex[-2:], frame)
        frame = self.__set_frame(5 * 2 - 1, 2, limit_hex[-4:-2], frame)
        frame = self.__set_frame(6 * 2 - 1, 2, limit_hex[-6:-4], frame)
        frame = self.__set_frame(7 * 2 - 1, 2, limit_hex[-8:-6], frame)
        frame = self.__get_check_sum(frame)
        logger.debug(f"set voltage limit frame : {frame}")
        self.__max_voltage = limit
        self.__send(frame)

    @check_connect("__connected", battery_tips)
    def set_voltage_value(self, value: float):
        """
        设置电源的输出电压

        :param value:  电源的输出电压值,必须介于0-最大电压(如18.000)之间，数据类型为float
        """
        if value < 0 or value > self.__max_voltage:
            raise ValueError(f"voltage output value over limit, max V should be {self.__max_voltage}")
        value = int(value * 1000)
        value_hex = hex(value)[2:]
        value_hex = '0000000' + value_hex
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '23', frame)
        frame = self.__set_frame(4 * 2 - 1, 2, value_hex[-2:], frame)
        frame = self.__set_frame(5 * 2 - 1, 2, value_hex[-4:-2], frame)
        frame = self.__set_frame(6 * 2 - 1, 2, value_hex[-6:-4], frame)
        frame = self.__set_frame(7 * 2 - 1, 2, value_hex[-8:-6], frame)
        frame = self.__get_check_sum(frame)
        logger.debug(f"set voltage output value frame : {frame}")
        return self.__send(frame)

    @check_connect("__connected", battery_tips)
    def set_current_value(self, value: float):
        """
        设置电源的输出电流

        :param value: 电源的输出电流值,必须介于0-最大电流(10.000A)之间，数据类型为float
        """
        if value < 0 or value > self.__max_current:
            raise ValueError(f"current output value over limit, max I should be {self.__max_current}")
        value = int(value * 1000)
        value_hex = hex(value)[2:]
        value_hex = '000' + value_hex
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '24', frame)
        frame = self.__set_frame(4 * 2 - 1, 2, value_hex[-2:], frame)
        frame = self.__set_frame(5 * 2 - 1, 2, value_hex[-4:-2], frame)
        frame = self.__get_check_sum(frame)
        logger.debug(f"set current output value frame : {frame}")
        self.__send(frame)

    @check_connect("__connected", battery_tips)
    def set_power_supply_address(self, address: str):
        """
        设置电源的新地址

        :param address: 电源的新地址，字符串类型
        """
        if len(address) != 2:
            raise ValueError("power supply length must be 2, change address failed.")
        address_hex = bytes.fromhex(address).hex()
        address_int = int(address_hex, 16)
        if address_int < 0 or address_int > 254:
            logger.info("address must be smaller than 0xfe.")
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '25', frame)
        frame = self.__set_frame(4 * 2 - 1, 2, address, frame)
        frame = self.__get_check_sum(frame)
        self.__address = address
        logger.debug(f"new address is: {address}, set power supply address frame: {frame}")
        self.__send(frame)

    def get_all_status(self) -> Status:
        """
        读取电源的电流、电压和电源状态

        :return: 电源的电流、电压等所有状态，以Status状态返回
        """
        battery_status = Status()
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '26', frame)
        frame = self.__get_check_sum(frame)
        self.__send(frame)
        sleep(1)
        logger.debug(f"send command to get status, frame : {frame}")
        result_contents = self.__serial.read_all(True)
        # 没有收到数据直接返回
        if not result_contents:
            return battery_status
        # 收到数据把标志职位True表示可用
        else:
            battery_status.available_flag = True
        result = [hex(e)[2:] for e in list(result_contents)]
        logger.debug(f"data retrieved from serial port: {result} and length = {len(result)}")
        result_bytes = []
        for byte in result:
            result_bytes.append(("0" + byte) if len(byte) == 1 else byte)
        logger.debug(f"result_bytes = {result_bytes}")
        # 确定以26开头的数据
        position = -1
        for i, byte in enumerate(result_bytes):
            if byte == 'aa' and result_bytes[i + 1] == self.__address and result_bytes[i + 2] == '26':
                if i + 26 <= len(result_bytes):
                    position = i
        logger.debug(f"position = {position}")
        status_bytes = result_bytes[position:position + 26]
        # 开始处理
        logger.debug(f"get power supply all status: {status_bytes} and length = {len(status_bytes)}")
        battery_status.current = int(status_bytes[4] + status_bytes[3], 16) / 1000
        battery_status.voltage = int(status_bytes[8] + status_bytes[7] + status_bytes[6] + status_bytes[5], 16) / 1000
        power_status = bin(int(status_bytes[9], 16))
        content = power_status[2:]
        if len(content) < 8:
            for i in range(8 - len(content)):
                content = "0" + content
        power_status = content
        logger.debug(f"power_status value = {power_status}")
        battery_status.power = int(power_status[-1])
        battery_status.over_hot = int(power_status[-2])
        battery_status.remote = int(power_status[-8])
        power_status_value = power_status[-4:-2]
        if power_status_value == '01':
            battery_status.output_mode = 'CV'
        elif power_status_value == '10':
            battery_status.output_mode = 'CC'
        elif power_status_value == '11':
            battery_status.output_mode = 'Unreg'
        else:
            battery_status.output_mode = 'None'
        battery_status.fan_level = int(power_status[-7:-4], 2)
        battery_status.set_current = int(status_bytes[11] + status_bytes[10], 16) / 1000
        battery_status.max_voltage = int(status_bytes[15] + status_bytes[14] + status_bytes[13] + status_bytes[12],
                                         16) / 1000
        battery_status.set_voltage = int(status_bytes[19] + status_bytes[18] + status_bytes[17] + status_bytes[16],
                                         16) / 1000
        logger.debug(f"is get power supply all status : {battery_status.available_flag}")
        return battery_status

    @check_connect("__connected", battery_tips)
    def set_power_calibrate_protect_status(self, switch: bool):
        """
        设置电源校准保护状态

        :param switch:
            True: 保护

            False: 不保护
        """
        if switch:
            mode = "01"
        else:
            mode = "00"
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '27', frame)
        frame = self.__set_frame(4 * 2 - 1, 2, mode, frame)
        frame = self.__set_frame(5 * 2 - 1, 2, '28', frame)
        frame = self.__set_frame(6 * 2 - 1, 2, '01', frame)
        frame = self.__get_check_sum(frame)
        logger.debug(f"set power calibrate protect status frame is : {frame}")
        self.__send(frame)

    @check_connect("__connected", battery_tips)
    def get_power_calibrate_protect_status(self) -> bool:
        """
        读取电源校准保护状态

        :return:
            False 为保护失能

            True 为保护使能
        """
        frame = self.__get_frame()
        frame = self.__set_frame(3 * 2 - 1, 2, '28', frame)
        frame = self.__get_check_sum(frame)
        logger.debug(f"get power calibrate protect status frame is : {frame}")
        self.__send(frame)
        result = self.__serial.read_bytes(len(frame), False)
        result = [hex(e)[2:] for e in list(result)]
        logger.debug(f"get power calibrate protect status as hex : {result}")
        return int(result[3], 16) == 1
