# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        zlg_device
# @Author:      philosophy
# @Created:     2022/02/19 - 22:44
# --------------------------------------------------------
import os
import platform
from ctypes import CDLL, POINTER, CFUNCTYPE, c_uint, c_char_p, byref, c_int
from typing import Tuple, Any

from ..checker import control_decorator, check_connect, can_tips
from .zlg_basic import ZCAN_USBCANFD_200U, ZCAN_TYPE_CANFD, ZCAN_TYPE_CAN, \
    INVALID_DEVICE_HANDLE, IProperty, ZCAN_CHANNEL_INIT_CONFIG, ZCAN_STATUS_OK, ZCAN_DEVICE_INFO, \
    ZCAN_Transmit_Data, ZCAN_TransmitFD_Data, ZCAN_Receive_Data, ZCAN_ReceiveFD_Data, BAUD_RATE, DATA_RATE
from ..logger import logger
from .message import Message
from .abstract_class import BaudRateEnum, BaseCanDevice


class ZlgUsbCanDevice(BaseCanDevice):

    def __init__(self, is_fd: bool = True):
        """

        :param is_fd:
        """
        super().__init__()
        # 设备类型号,TODO 目前仅支持200U这个，MINI不支持，后续需要支持再说
        self.__device_type = ZCAN_USBCANFD_200U
        self.__is_fd = is_fd
        # 设备索引号，用于区分一台计算机上使用的多套同类型设备。如只插 1 台USBCANFD 设备， device_index=0；
        self.__device_index = c_uint(0)
        # CAN通道号
        self.__channel_index = None
        self.__dll_path = self.__get_dll_path()
        self.__device_handler = None
        self.__channel_handler = None
        logger.debug(f"use dll path is {self.__dll_path}")
        if platform.system() == "Windows":
            self.__lib_can = CDLL(self.__dll_path)
        else:
            raise RuntimeError("can not support linux")

    @staticmethod
    def __get_dll_path():
        system_bit = platform.architecture()[0]
        if system_bit == "32bit":
            dll_path = r'\zlg\x86\zlgcan.dll'
        else:
            dll_path = r'\zlg\x64\zlgcan.dll'
        return os.path.split(os.path.realpath(__file__))[0] + dll_path

    def __set_value(self, iproperty, type_: str, value: str):
        func = CFUNCTYPE(c_uint, c_char_p, c_char_p)(iproperty.contents.SetValue)
        path = f"{self.__channel_index}/{type_}"
        ret = func(c_char_p(path.encode("utf-8")), c_char_p(value.encode("utf-8")))
        if ret != ZCAN_STATUS_OK:
            raise RuntimeError(f"set {type_} failed")
        else:
            self.__lib_can.ReleaseIProperty(iproperty)

    def __init_device(self, baud_rate: BaudRateEnum, data_rate: BaudRateEnum):
        self.__lib_can.GetIProperty.restype = POINTER(IProperty)
        ip = self.__lib_can.GetIProperty(self.__device_handler)
        # https://manual.zlg.cn/web/#/152/6359
        self.__set_value(ip, "clock", "60000000")
        # 设置CANFD 控制器标准类型，ISO 或非 ISO，通常使用 ISO 标准
        self.__set_value(ip, "canfd_standard", "0")
        if baud_rate != BaudRateEnum.LOW:
            # USBCANFD 每通道内置 120Ω终端电阻，可通过属性设置选择使能或不使能。
            self.__set_value(ip, "initenal_resistance", "1")
        else:
            # USBCANFD 每通道内置 120Ω终端电阻，可通过属性设置选择使能或不使能。
            self.__set_value(ip, "initenal_resistance", "0")
        can_config = ZCAN_CHANNEL_INIT_CONFIG()
        # 操作类型 只支持CANFD，发标准CAN的时候仍然用CANFD方式
        # can_config.can_type = ZCAN_TYPE_CANFD if self.__is_fd else ZCAN_TYPE_CAN
        can_config.can_type = ZCAN_TYPE_CANFD
        # 工作模式，=0表示正常模式（相当于正常节点），=1表示只听模式（只接收，不影响总线）。
        can_config.config.canfd.mode = 0
        can_config.config.canfd.abit_timing = BAUD_RATE[baud_rate.value]
        can_config.config.canfd.dbit_timing = DATA_RATE[data_rate.value]
        self.__channel_handler = self.__lib_can.ZCAN_InitCAN(self.__device_handler, self.__channel_index, can_config)
        if self.__channel_handler is None:
            raise RuntimeError("init can failed")

    @control_decorator
    def __start_device(self):
        return self.__lib_can.ZCAN_StartCAN(self.__channel_handler)

    def __data_package(self, message: Message, transmit_num: int = 1):
        if self.__is_fd:
            logger.trace("package canfd")
            msgs = (ZCAN_TransmitFD_Data * transmit_num)()
            for i in range(transmit_num):
                # 发送方式，0=正常发送，1=单次发送，2=自发自收，3=单次自发自收。
                msgs[i].transmit_type = 1
                msgs[i].frame.can_id = message.msg_id
                msgs[i].frame.len = self._dlc[len(message.data)]
                for j, value in enumerate(message.data):
                    msgs[i].frame.data[j] = value
        else:
            logger.trace("package can")
            msgs = (ZCAN_Transmit_Data * transmit_num)()
            for i in range(transmit_num):
                # 发送方式，0=正常发送，1=单次发送，2=自发自收，3=单次自发自收。
                msgs[i].transmit_type = 1
                msgs[i].frame.can_id = message.msg_id
                msgs[i].frame.can_dlc = self._dlc[len(message.data)]
                for j, value in enumerate(message.data):
                    msgs[i].frame.data[j] = value
        return msgs

    def __open_device(self, reserved: int = 0):
        """
        DEVICE_HANDLE  ZCAN_OpenDevice(
        　　UINT device_type,
        　　UINT device_index,
        　　UINT reserved);
        参数
        　　device_type
        　　设备类型，详见头文件zlgcan.h中的宏定义。
        　　device_index
        　　设备索引号，比如当只有一个USBCANFD-200U时，索引号为0，这时再插入一个USBCANFD-200U，那么后面插入的这个设备索引号就是1，以此类推。
        　　reserved
        　　仅作保留。
        返回值
        　　为INVALID_DEVICE_HANDLE表示操作失败，否则表示操作成功，返回设备句柄值，请保存该句柄值，往后的操作需要使用。
        :param reserved:
        :return:
        """
        reversed_ = c_uint(reserved)
        self.__device_handler = self.__lib_can.ZCAN_OpenDevice(self.__device_type, self.__device_index, reversed_)
        if self.__device_handler == INVALID_DEVICE_HANDLE:
            self._is_open = False
            raise RuntimeError("open device failed")
        else:
            self._is_open = True

    def open_device(self, baud_rate: BaudRateEnum = BaudRateEnum.HIGH, data_rate: BaudRateEnum = BaudRateEnum.DATA,
                    channel: int = 1):
        self.__channel_index = channel - 1
        if not self._is_open:
            self.__open_device()
        if self._is_open:
            logger.debug("device is opened")
            self.__init_device(baud_rate, data_rate)
            self.__start_device()

    def close_device(self):
        if self._is_open:
            if self.__lib_can.ZCAN_CloseDevice(self.__device_handler) == 1:
                self._is_open = False
                self.__channel_handler = None
                self.__channel_index = None
                logger.debug(f"device is closed")

    @check_connect("_is_open", can_tips)
    def read_board_info(self) -> str:
        info = ZCAN_DEVICE_INFO()
        ret = self.__lib_can.ZCAN_GetDeviceInf(self.__device_handler, byref(info))
        return ret if ret == ZCAN_STATUS_OK else "read failed"

    @check_connect("_is_open", can_tips)
    @control_decorator
    def reset_device(self):
        return self.__lib_can.ZCAN_ResetCAN(self.__device_handler)

    @check_connect("_is_open", can_tips)
    def transmit(self, message: Message):
        # 只发一条message
        transmit_num = 1
        msgs = self.__data_package(message, transmit_num)
        if self.__is_fd:
            logger.trace("transmit fd")
            result = self.__lib_can.ZCAN_TransmitFD(self.__channel_handler, msgs, transmit_num)
            if result != ZCAN_STATUS_OK:
                raise RuntimeError("transmit fd failed")
        else:
            logger.trace("transmit can")
            result = self.__lib_can.ZCAN_Transmit(self.__channel_handler, msgs, transmit_num)
            if result != ZCAN_STATUS_OK:
                raise RuntimeError("transmit failed")

    @check_connect("_is_open", can_tips)
    def receive(self, wait_time=c_int(-1)) -> Tuple[int, Any]:
        if self.__is_fd:
            rcv_num = self.__lib_can.ZCAN_GetReceiveNum(self.__channel_handler, ZCAN_TYPE_CANFD)
            logger.trace(f"receive count is {rcv_num}")
            if rcv_num:
                rcv_canfd_msgs = (ZCAN_ReceiveFD_Data * rcv_num)()
                counts = self.__lib_can.ZCAN_ReceiveFD(self.__channel_handler, byref(rcv_canfd_msgs), rcv_num,
                                                       wait_time)
                logger.info(f"real receive count is {counts}")
                return counts, rcv_canfd_msgs
            else:
                raise RuntimeError("receive failed")
        else:
            rcv_num = self.__lib_can.ZCAN_GetReceiveNum(self.__channel_handler, ZCAN_TYPE_CAN)
            logger.trace(f"receive count is {rcv_num}")
            if rcv_num:
                rcv_can_msgs = (ZCAN_Receive_Data * rcv_num)()
                counts = self.__lib_can.ZCAN_Receive(self.__channel_handler, byref(rcv_can_msgs), rcv_num, wait_time)
                logger.info(f"real receive count is {counts}")
                return counts, rcv_can_msgs
            else:
                raise RuntimeError("receive buffer not  failed")
