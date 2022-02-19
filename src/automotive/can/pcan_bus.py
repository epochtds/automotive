# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        pcan_bus
# @Author:      philosophy
# @Created:     2022/02/19 - 22:51
# --------------------------------------------------------
from time import sleep
from ..logger import logger
from .pcan_device import PCanDevice
from .abstract_class import BaseCanBus, BaudRateEnum
from .message import Message


class PCanBus(BaseCanBus):
    """
        实现CANBus接口，能够多线程发送和接收can信号
    """

    def __init__(self, baud_rate: BaudRateEnum = BaudRateEnum.HIGH, data_rate: BaudRateEnum = BaudRateEnum.DATA,
                 channel_index: int = 1, can_fd: bool = False, max_workers: int = 300):
        if can_fd:
            raise RuntimeError("pcan not support canfd")
        super().__init__(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index,
                         can_fd=can_fd, max_workers=max_workers)
        # PCAN实例化
        self._can = PCanDevice(can_fd)

    @staticmethod
    def __get_data(data, length: int) -> list:
        """
        转换pcan收的data为list

        :param data: 收到的data数据

        :param length:  长度

        :return: 8byte的list对象
        """
        msg_data = []
        for i in range(length):
            msg_data.append(data[i])
        return msg_data

    @staticmethod
    def __get_time_stamp(timestamp) -> int:
        """
        peak CAN获取时间方法

        :param timestamp:  peak can读取的时间

        :return: 转换后的时间 (毫秒)
        """
        time_stamp = timestamp.micros + 1000 * timestamp.millis + 0x100000000 * 1000 * timestamp.millis_overflow
        return int(time_stamp / 1000)

    def __get_message(self, message, timestamp) -> Message:
        """
        获取message对象

        :param message: message信息

        :return: PeakCanMessage对象
        """
        msg = Message()
        msg.msg_id = message.id
        msg.time_stamp = self.__get_time_stamp(timestamp)
        msg.send_type = message.msg_type
        msg.data_length = 8 if message.len > 8 else message.len
        msg.data = self.__get_data(message.data, msg.data_length)
        return msg

    def __receive(self):
        """
        CAN接收帧函数，在接收线程中执行
        """
        while self._can.is_open and self._need_receive:
            try:
                receive_msg, timestamp = self._can.receive()
                msg_id = receive_msg.id
                logger.trace(f"msg id = {hex(msg_id)}")
                receive_message = self.__get_message(receive_msg, timestamp)
                self._receive_messages[msg_id] = receive_message
                self._stack.append(receive_message)
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
