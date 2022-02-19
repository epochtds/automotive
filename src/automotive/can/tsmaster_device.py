# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        tsmaster_device
# @Author:      philosophy
# @Created:     2022/02/19 - 22:44
# --------------------------------------------------------
import os
import platform
from ctypes import CDLL, byref, c_size_t, c_int32, c_double, c_ubyte, POINTER, cast, c_int
from typing import List, Tuple, Any
from .tsmaster_basic import TRUE, APP_CHANNEL, TLIBCANFDControllerMode, TLIBCANFDControllerType, TLibCAN, TLibCANFD, \
    FALSE
from ..checker import tsmaster_control_decorator, check_connect, can_tips
from .abstract_class import BaseCanDevice, BaudRateEnum
from ..logger import logger
from .message import Message


class TSMasterDevice(BaseCanDevice):

    def __init__(self, is_fd: bool = False):
        super().__init__()
        self.__is_fd = is_fd
        self.__device_handler = c_size_t(0)
        self.__channel = None
        # 需要在硬件文档中查询获取
        self.__dll_path = self.__get_dll_path()
        logger.debug(f"use dll path is {self.__dll_path}")
        if platform.system() == "Windows":
            self.__lib_can = CDLL(self.__dll_path)
        else:
            raise RuntimeError("can not support linux")

    @staticmethod
    def __get_dll_path() -> str:
        """
        获取dll的绝对路径路径

        :return 返回dll所在的绝对路径
        """
        system_bit = platform.architecture()[0]
        if system_bit == "32bit":
            dll_path = r'\tsmaster\x86\libTSCAN.dll'
        else:
            dll_path = r'\tsmaster\x64\libTSCAN.dll'
        abs_dll = os.path.split(os.path.realpath(__file__))[0] + dll_path
        logger.debug(f"use dll {abs_dll}")
        return abs_dll

    def __init_device(self):
        # //初始化TSCANAPI模块
        # typedef void(__stdcall* initialize_lib_tscan_t)(bool AEnableFIFO,bool AEnableTurbe);
        self.__lib_can.initialize_lib_tscan(TRUE, FALSE)

    def __scan_devices(self):
        # //扫描在线的设备
        # typedef uint32_t(__stdcall* tscan_scan_devices_t)(uint32_t* ADeviceCount);
        # 定义函数返回类型
        self.__lib_can.tscan_scan_devices(byref(c_int32(1)))

    # @tsmaster_control_decorator
    # def __configure_can(self, baud_rate: float, channel: int):
    #     # //设置CAN报文波特率参数
    #     # typedef c_uint(__stdcall* tscan_config_can_by_BaudRateEnum_t)(const size_t ADeviceHandle, const APP_CHANNEL AChnIdx, const c_double ARateKbps, const c_uint A120OhmConnected);
    #     return self.__lib_can.tscan_config_can_by_baudrate(self.__device_handler,
    #                                                        APP_CHANNEL[channel],
    #                                                        c_double(baud_rate),
    #                                                        c_uint(1))

    @tsmaster_control_decorator
    def __configure_can(self, baud_rate: float, data_rate: float, channel: int, is_can_fd: bool = False,
                        is_iso_can_fd: bool = True):
        # //设置CANFD报文波特率参数
        # typedef c_uint(__stdcall* tscan_config_canfd_by_baudrate_t)(const size_t  ADeviceHandle, const APP_CHANNEL AChnIdx,
        # const c_double AArbRateKbps, const c_double ADataRateKbps, const TLIBCANFDControllerType AControllerType,
        # 	const TLIBCANFDControllerMode AControllerMode, const c_uint A120OhmConnected);
        if is_can_fd:
            if is_iso_can_fd:
                controller_type = "ISOCAN"
            else:
                controller_type = "NonISOCAN"
        else:
            controller_type = "ISOCAN"
        can_fd_controller_mode = "Normal"
        logger.debug(f"controller_type = {controller_type}")
        return self.__lib_can.tscan_config_canfd_by_baudrate(self.__device_handler,
                                                             APP_CHANNEL[channel],
                                                             c_double(baud_rate),
                                                             c_double(data_rate),
                                                             TLIBCANFDControllerType[controller_type],
                                                             TLIBCANFDControllerMode[can_fd_controller_mode],
                                                             TRUE)

    def __set_baud_rate(self, baud_rate: float, data_rate: float, channel: int):
        # 设置波特率
        logger.debug(f"baud_rate is {baud_rate}, channel is {channel}")
        self.__configure_can(baud_rate, data_rate, channel, self.__is_fd)

    def __open_device(self):
        self.__init_device()
        self.__scan_devices()

    @tsmaster_control_decorator
    def __disconnect(self):
        return self.__lib_can.tsapp_disconnect()

    def __data_package(self, data: List, msg_id: int) -> TLibCAN:
        lib_can = TLibCAN()
        lib_can.FIdxChn = self.__channel - 1
        lib_can.FIdentifier = msg_id
        lib_can.FProperties = 1
        lib_can.FDLC = self._dlc[len(data)]
        # CAN帧的数据
        for j, data in enumerate(data):
            lib_can.FData[j] = data
        return lib_can

    def __data_package_fd(self, data: List, msg_id: int) -> TLibCANFD:
        lib_can_fd = TLibCANFD()
        lib_can_fd.FIdxChn = self.__channel - 1
        lib_can_fd.FIdentifier = msg_id
        lib_can_fd.FProperties = 1
        lib_can_fd.FFDProperties = 1
        # DLC不是简单的长度，而需要对应关系
        lib_can_fd.FDLC = self._dlc[len(data)]
        for j, data in enumerate(data):
            lib_can_fd.FData[j] = data
        return lib_can_fd

    def open_device(self, baud_rate: BaudRateEnum = BaudRateEnum.HIGH, data_rate: BaudRateEnum = BaudRateEnum.DATA,
                    channel: int = 1):
        self.__channel = channel
        if not self._is_open:
            self.__open_device()
            # 连接CAN盒
            # //连接设备，ADeviceSerial !=NULL：连接指定的设备；ADeviceSerial == NULL：连接默认设备
            # typedef uint32_t(__stdcall* tscan_connect_t)(const char* ADeviceSerial, size_t* AHandle);
            # self.__lib_can.tscan_connect.argtypes = (CHAR_P, POINTER(U))
            # self.__lib_can.tscan_connect.restype = c_uint
            result = self.__lib_can.tscan_connect('', byref(self.__device_handler))
            if result == 0:
                logger.info("ts master connect")
                self._is_open = True
                self.__set_baud_rate(baud_rate.value, data_rate.value, channel)
            else:
                self._is_open = False
                raise RuntimeError(f"open tsmaster failed, result is {result}")

    def close_device(self):
        if self._is_open:
            logger.trace("tscan_disconnect_all_devices")
            # //断开所有设备
            # typedef c_uint(__stdcall* tscan_disconnect_all_devices_t)(void);
            result = self.__lib_can.tscan_disconnect_all_devices()
            if result == 0:
                self._is_open = False
                self.__channel = None
                # //释放TSCANAPI模块
                # typedef void(__stdcall* finalize_lib_tscan_t)(void);
                # logger.trace("try to finalize_lib_tscan")
                # self.__lib_can.finalize_lib_tscan()
            else:
                raise RuntimeError(f"close tsmaster failed, result = {result}")

    @check_connect("_is_open", can_tips)
    def transmit(self, message: Message):
        if self.__is_fd:
            logger.trace("transmit by can fd")
            etcan_fd = self.__data_package_fd(message.data, message.msg_id)
            # //异步发送CANFD报文
            # typedef c_uint(__stdcall* tscan_transmit_canfd_async_t)(const size_t ADeviceHandle, const TLibCANFD* ACAN);
            result = self.__lib_can.tscan_transmit_canfd_async(self.__device_handler, etcan_fd)
            if result != 0:
                raise RuntimeError(f"transmit can fd failed. error code is {result}")
        else:
            logger.trace("transmit by can")
            etcan = self.__data_package(message.data, message.msg_id)
            # //异步发送CAN报文
            # typedef c_uint(__stdcall* tscan_transmit_can_async_t)(const size_t ADeviceHandle, const TLibCAN* ACAN);
            result = self.__lib_can.tscan_transmit_can_async(self.__device_handler, etcan)
            if result != 0:
                raise RuntimeError(f"transmit failed. error code is {result}")

    @check_connect("_is_open", can_tips)
    def receive(self) -> Tuple[int, Any]:
        # 设置缓存大小， 这个是IN OUT模式，即输入的2500不代表一定有这么多数据，这个只是一个最大值，在执行完成函数后在读取值能知道实际的数量
        buffer_size = 2500
        p_buffer_size = byref(c_int(buffer_size))
        if self.__is_fd:
            # //读取CANFD报文
            # //ADeviceHandle：设备句柄；ACANBuffers:存储接收报文的数组；ACANBufferSize：存储数组的长度
            # //返回值：实际收到的报文数量
            # typedef c_uint(__stdcall* tsfifo_receive_canfd_msgs_t)(const size_t ADeviceHandle, const TLibCANFD* ACANBuffers, c_uint ACANBufferSize, c_uint8 AChn, c_uint8 ARXTX);
            # 0-RX, 1-TX
            p_receive = [TLibCANFD() for _ in range(buffer_size)]
            data = POINTER(TLibCANFD * len(p_receive))((TLibCANFD * len(p_receive))(*p_receive))
            result = self.__lib_can.tsfifo_receive_canfd_msgs(self.__device_handler,
                                                              data,
                                                              p_buffer_size,
                                                              APP_CHANNEL[self.__channel],
                                                              c_ubyte(0))
        else:
            # //读取CAN报文
            # //ADeviceHandle：设备句柄；ACANBuffers:存储接收报文的数组；ACANBufferSize：存储数组的长度
            # //返回值：实际收到的报文数量
            # typedef c_uint(__stdcall* tsfifo_receive_can_msgs_t)(const size_t ADeviceHandle, const TLibCAN* ACANBuffers, c_uint ACANBufferSize, c_uint8 AChn, c_uint8 ARXTX);
            # 0-RX, 1-TX
            # p_receive = (TLibCAN * buffer_size)()
            # temp_size = copy.copy(p_buffer_size)
            p_receive = [TLibCAN() for _ in range(buffer_size)]
            data = POINTER(TLibCAN * len(p_receive))((TLibCAN * len(p_receive))(*p_receive))
            result = self.__lib_can.tsfifo_receive_can_msgs(self.__device_handler,
                                                            data,
                                                            p_buffer_size,
                                                            APP_CHANNEL[self.__channel],
                                                            c_ubyte(0))
        if result == 0:
            # 真实收到的数据长度
            cast_value = cast(p_buffer_size, POINTER(c_int32)).contents.value
            # print(cast_value)
            return cast_value, data.contents
        else:
            raise RuntimeError(f"receive failed, frame receive count is {result}")
