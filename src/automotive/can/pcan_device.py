# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        pcan_device.py
# @Author:      philosophy
# @Created:     2022/02/19 - 22:24
# --------------------------------------------------------
# 导入所需模块
from inspect import stack
from ctypes import memmove, c_uint
from typing import List, Any, Tuple

from . import pcan_basic
from ..logger import logger
from .abstract_class import BaseCanDevice, BaudRateEnum
from ..checker import check_connect, can_tips
from .message import Message

baud_rate_list = {
    #   波特率
    5: pcan_basic.PCAN_BAUD_5K,
    10: pcan_basic.PCAN_BAUD_10K,
    20: pcan_basic.PCAN_BAUD_20K,
    33: pcan_basic.PCAN_BAUD_33K,
    47: pcan_basic.PCAN_BAUD_47K,
    50: pcan_basic.PCAN_BAUD_50K,
    83: pcan_basic.PCAN_BAUD_83K,
    95: pcan_basic.PCAN_BAUD_95K,
    100: pcan_basic.PCAN_BAUD_100K,
    125: pcan_basic.PCAN_BAUD_125K,
    250: pcan_basic.PCAN_BAUD_250K,
    500: pcan_basic.PCAN_BAUD_500K,
    800: pcan_basic.PCAN_BAUD_800K,
    1000: pcan_basic.PCAN_BAUD_1M
}

hw_types = {'ISA-82C200': pcan_basic.PCAN_TYPE_ISA,
            'ISA-SJA1000': pcan_basic.PCAN_TYPE_ISA_SJA,
            'ISA-PHYTEC': pcan_basic.PCAN_TYPE_ISA_PHYTEC,
            'DNG-82C200': pcan_basic.PCAN_TYPE_DNG,
            'DNG-82C200 EPP': pcan_basic.PCAN_TYPE_DNG_EPP,
            'DNG-SJA1000': pcan_basic.PCAN_TYPE_DNG_SJA,
            'DNG-SJA1000 EPP': pcan_basic.PCAN_TYPE_DNG_SJA_EPP}

io_ports = {'0100': 0x100, '0120': 0x120, '0140': 0x140, '0200': 0x200, '0220': 0x220, '0240': 0x240,
            '0260': 0x260, '0278': 0x278, '0280': 0x280, '02A0': 0x2A0, '02C0': 0x2C0, '02E0': 0x2E0,
            '02E8': 0x2E8, '02F8': 0x2F8, '0300': 0x300, '0320': 0x320, '0340': 0x340, '0360': 0x360,
            '0378': 0x378, '0380': 0x380, '03BC': 0x3BC, '03E0': 0x3E0, '03E8': 0x3E8, '03F8': 0x3F8}

interrupts = {'3': 3, '4': 4, '5': 5, '7': 7, '9': 9, '10': 10, '11': 11, '12': 12, '15': 15}


# ===============================================================================
# 封装pcan_basic的接口
class PCanDevice(BaseCanDevice):

    def __init__(self, is_fd: bool = False):
        """
        """
        super().__init__()
        self.__can_basic = pcan_basic.PCANBasic()
        self.__channel = pcan_basic.PCAN_USBBUS1
        #  是否CANFD，如果是CANFD则调用canfd接口
        self.__is_fd = is_fd

    def __init_device(self, baud_rate: str, channel: int):
        """
        Initializes a PEAK CAN Channel

        :param baud_rate: 波特率

        :param channel: A TPCANHandle representing a PEAK CAN Channel
        """
        # 由于目前peak can只支持单通道，所以无论设置还是不设置该值都是PCAN_USBBUS1
        if channel == 1:
            channel = self.__channel
        else:
            raise RuntimeError("peak can only support 1 channel")
        btr0btr1 = baud_rate_list[baud_rate]
        # TIPS: 目前只支持IPEH-002021 这个型号，该型号不支持CAN FD
        hw_type = hw_types['ISA-82C200']
        io_port = io_ports['0100']
        interrupt = interrupts['11']

        if not self._is_open:
            if self.__is_fd:
                ret = self.__can_basic.initialize_fd(channel, btr0btr1)
            else:
                ret = self.__can_basic.initialize(channel, btr0btr1, hw_type, io_port, interrupt)
            if ret == 0:
                self._is_open = True
                logger.debug(f"pcan is open success")
            else:
                self._is_open = False
                raise RuntimeError(f"Method <{stack()[0][3]}> Init PEAK CAN channel_{hex(channel.value)} Failed.")

    @staticmethod
    def __data_package_fd(frame_length: int, message_id: int, send_type: int, data_length: int, data: List[Any]):
        """
        组包CAN FD发送数据，供VCI_Transmit函数使用。

        :param frame_length: 帧长度

        :param message_id:  11/29-bit message identifier

        :param send_type: Type of the message

        :param data_length: Data Length Code of the message (0..8)

        :param data: Data of the message (DATA[0]..DATA[7])

        :return: 返回组包的帧数据。
        """
        send_data = (pcan_basic.TPCANMsgFD * frame_length)()

        for i in range(frame_length):
            # 帧ID。32位变量，数据格式为靠右对齐
            send_data[i].ID = c_uint(message_id)

            # 发送帧类型。=0时为正常发送（发送失败会自动重发，重发最长时间为1.5-3秒）；
            # =1时为单次发送（只发送一次，不自动重发）；
            # 其它值无效。（二次开发，建议SendType=1，提高发送的响应速度）
            send_data[i].MSGTYPE = pcan_basic.TPCANMessageType(send_type)

            # 数据长度 DLC (<=8)，即CAN帧Data有几个字节。约束了后面Data[8]中的有效字节
            send_data[i].DLC = data_length

            # CAN帧的数据
            a_data = (pcan_basic.TPCANMessageType * 8)()
            for j, value in enumerate(data):
                a_data[j] = pcan_basic.TPCANMessageType(value)
            memmove(send_data[i].DATA, a_data, 8)
        return send_data

    @staticmethod
    def __data_package(frame_length: int, message_id: int, send_type: int, data_length: int, data: List[Any]):
        """
        组包CAN发送数据，供VCI_Transmit函数使用。

        :param frame_length: 帧长度

        :param message_id:  11/29-bit message identifier

        :param send_type: Type of the message

        :param data_length: Data Length Code of the message (0..8)

        :param data: Data of the message (DATA[0]..DATA[7])

        :return: 返回组包的帧数据。
        """
        send_data = (pcan_basic.TPCANMsg * frame_length)()

        for i in range(frame_length):
            # 帧ID。32位变量，数据格式为靠右对齐
            send_data[i].id = c_uint(message_id)

            # 发送帧类型。=0时为正常发送（发送失败会自动重发，重发最长时间为1.5-3秒）；
            # =1时为单次发送（只发送一次，不自动重发）；
            # 其它值无效。（二次开发，建议SendType=1，提高发送的响应速度）
            send_data[i].msg_type = pcan_basic.TPCANMessageType(send_type)

            # 数据长度 DLC (<=8)，即CAN帧Data有几个字节。约束了后面Data[8]中的有效字节
            send_data[i].len = data_length

            # CAN帧的数据
            a_data = (pcan_basic.TPCANMessageType * 8)()
            for j, value in enumerate(data):
                a_data[j] = pcan_basic.TPCANMessageType(value)
            memmove(send_data[i].data, a_data, 8)
        return send_data

    def open_device(self, baud_rate: BaudRateEnum = BaudRateEnum.HIGH, data_rate: BaudRateEnum = BaudRateEnum.DATA,
                    channel: int = 1):
        """
        打开Pcan设备

        :param data_rate: DATA速率，对于目前的PCAN没有用
        :param baud_rate: CAN速率，HIGH表示高速，LOW表示低速

        :param channel:
            A TPCANHandle representing a PEAK CAN Channel

        :return: A TPCANStatus error code
        """
        baud_rate = baud_rate.value
        logger.debug(f"baud_rate is {baud_rate}")
        if channel != 1:
            raise RuntimeError("pcan channel only support 1")
        self.__init_device(baud_rate, channel)

    def close_device(self):
        """
        Un_initializes one or all PEAK CAN Channels initialized by CAN_Initialize。

        :return: A TPCANStatus error code
        """
        channel = self.__channel
        if self._is_open:
            ret = self.__can_basic.uninitialize(channel)
            if ret == pcan_basic.PCAN_ERROR_OK:
                logger.debug(f"close pcan success")
                self._is_open = False
            else:
                logger.error(f"Method <{stack()[0][3]}> Close PEAK CAN Failed.")

    @check_connect("_is_open", can_tips)
    def transmit(self, message: Message, channel: int = None):
        """
        Transmits a CAN message。

        :param message: PeakCanMessage消息对象

        :param channel:  A TPCANHandle representing a PEAK CAN Channel
        """
        channel = self.__channel if channel else pcan_basic.PCAN_USBBUS1
        if self.__is_fd:
            p_send = self.__data_package_fd(message.frame_length,
                                            message.msg_id,
                                            message.send_type,
                                            message.data_length,
                                            message.data)
        else:
            p_send = self.__data_package(message.frame_length,
                                         message.msg_id,
                                         message.send_type,
                                         message.data_length,
                                         message.data)
        try:
            ret = self.__can_basic.write(channel, p_send)
            if ret == pcan_basic.PCAN_ERROR_OK:
                logger.trace(f"PEAK CAN channel_{hex(channel.value)} Transmit Success.")
            else:
                raise RuntimeError(f"PEAK CAN channel_{hex(channel.value)} Transmit Failed.")
        except Exception as e:
            raise RuntimeError(f'PEAK CAN transmit failed. error info is {e}')

    @check_connect("_is_open", can_tips)
    def receive(self, channel: int = None) -> Tuple[Any, Any]:
        """
        Reads a CAN message from the receive queue of a PEAK CAN Channel

        :param channel: A TPCANHandle representing a PEAK CAN Channel

        :return: PeakCanMessage消息对象
        """
        channel = self.__channel if channel else pcan_basic.PCAN_USBBUS1
        try:
            if self.__is_fd:
                ret, message, timestamp = self.__can_basic.read_fd(channel)
            else:
                ret, message, timestamp = self.__can_basic.read(channel)
            if ret == pcan_basic.PCAN_ERROR_OK:
                logger.trace(f"PEAK CAN channel_{hex(channel.value)} Receive Success.")
                return message, timestamp
            else:
                raise RuntimeError(f"Method <{stack()[0][3]}> PEAK CAN Receive Failed.")
        except Exception:
            raise RuntimeError('PEAK CAN receive failed.')
