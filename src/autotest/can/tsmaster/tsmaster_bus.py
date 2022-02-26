# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        tsmaster_bus
# @Author:      philosophy
# @Created:     2022/02/19 - 22:51
# --------------------------------------------------------
from time import sleep
from typing import List

from autotest.logger import logger
from autotest.can.message import Message
from autotest.can.abstract_class import BaseCanBus, BaudRateEnum
from .tsmaster_device import TSMasterDevice


class TsMasterCanBus(BaseCanBus):

    def __init__(self, baud_rate: BaudRateEnum = BaudRateEnum.HIGH, data_rate: BaudRateEnum = BaudRateEnum.DATA,
                 channel_index: int = 1, can_fd: bool = False, max_workers: int = 300):
        super().__init__(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index, can_fd=can_fd,
                         max_workers=max_workers)
        # 实例化同星
        self._can = TSMasterDevice(can_fd)

    @staticmethod
    def __get_data(data, length: int) -> List:
        msg_data = []
        for i in range(length):
            msg_data.append(data[i])
        return msg_data

    def __get_message(self, p_receive) -> Message:
        """
        获取message对象

        :param p_receive: message信息

        :return: PeakCanMessage对象
        """
        msg = Message()
        msg.msg_id = p_receive.FIdentifier
        msg.time_stamp = p_receive.FTimeUS
        msg.data = self.__get_data(p_receive.FData, self._get_dlc_length(p_receive.FDLC))
        msg.data_length = len(msg.data)
        return msg

    def __receive(self):
        """
        CAN接收帧函数，在接收线程中执行
        """
        logger.debug(f"start receive and tsmaster status {self._can.is_open} and need_receive {self._need_receive}")
        while self._can.is_open and self._need_receive:
            try:
                count, p_receive = self._can.receive()
                logger.trace(f"receive count is {count}")
                # todo 同星的dll存在64bit， 标准can消息接收的问题，所以修改为过滤ID不为空的处理方式
                messages = list(filter(lambda x: x.FIdentifier != 0x00, p_receive))
                for p_receive in messages:
                    message = self.__get_message(p_receive)
                    logger.trace(f"message_id = {hex(message.msg_id)}")
                    self._receive_messages[message.msg_id] = message
                    self._stack.append(message)
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
