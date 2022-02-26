# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        usbcan_bus
# @Author:      philosophy
# @Created:     2022/02/19 - 22:51
# --------------------------------------------------------
from time import sleep
from autotest.logger import logger
from .usbcan_device import UsbCanDevice
from ..abstract_class import BaudRateEnum, CanBoxDeviceEnum, BaseCanBus
from ..message import Message


class UsbCanBus(BaseCanBus):
    """
    实现CANBus接口，能够多线程发送和接收can信号
    """

    def __init__(self, can_box_device: CanBoxDeviceEnum, baud_rate: BaudRateEnum = BaudRateEnum.HIGH,
                 data_rate: BaudRateEnum = BaudRateEnum.DATA, channel_index: int = 1, can_fd: bool = False,
                 max_workers: int = 300):
        super().__init__(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index, can_fd=can_fd,
                         max_workers=max_workers)
        if self._can_fd:
            raise RuntimeError("usb can not support can fd")
        # USB CAN BOX实例化
        self._can = UsbCanDevice(can_box_device)
        # Default TimeStamp有效
        self.__time_flag = 1

    @staticmethod
    def __get_data(data, length: int) -> list:
        """
        转换CAN BOX收的data为list

        :param data: 收到的data数据

        :param length:  长度

        :return: 8byte的列表
        """
        msg_data = []
        for i in range(length):
            msg_data.append(data[i])
        return msg_data

    @staticmethod
    def __get_reserved(reserved_value) -> list:
        """
        获取reversed参数

        :param reserved_value:  reversed的内容(can上收到的)

        :return: 解析后的列表
        """
        reserved_list = []
        for i in range(3):
            reserved_list.append(reserved_value[i])
        return reserved_list

    def __get_message(self, p_receive) -> Message:
        """
        获取message对象

        :param p_receive: message信息

        :return: PeakCanMessage对象
        """
        msg = Message()
        msg.msg_id = p_receive.id
        # 转换成毫秒
        msg.time_stamp = int(p_receive.time_stamp / 10)
        # msg.time_stamp = hex(p_receive.time_stamp)
        msg.time_flag = p_receive.time_flag
        msg.send_type = p_receive.send_type
        msg.remote_flag = p_receive.remote_flag
        msg.external_flag = p_receive.extern_flag
        msg.reserved = self.__get_reserved(p_receive.reserved)
        msg.data_length = 8 if p_receive.data_len > 8 else p_receive.data_len
        msg.data = self.__get_data(p_receive.data, msg.data_length)
        return msg

    def __receive(self):
        """
        CAN接收帧函数，在接收线程中执行
        """
        while self._can.is_open and self._need_receive:
            try:
                ret, p_receive = self._can.receive()
                logger.trace(f"return size is {ret}")
                for i in range(ret):
                    receive_message = self.__get_message(p_receive[i])
                    logger.trace(f"msg id = {hex(receive_message.msg_id)}")
                    # 单帧数据
                    if receive_message.external_flag == 0:
                        # 获取数据并保存到self._receive_msg字典中
                        self._receive_messages[receive_message.msg_id] = receive_message
                        self._stack.append(receive_message)
                    # 扩展帧
                    else:
                        logger.debug("type is external frame, not implement")
            except RuntimeError as e:
                logger.trace(e)
                continue
            finally:
                sleep(0.001)

    def open_can(self):
        """
        对CAN设备进行打开、初始化等操作，并同时开启设备的帧接收线程。
        """
        super()._open_can()
        # 把接收函数submit到线程池中
        self._receive_thread.append(self._thread_pool.submit(self.__receive))
