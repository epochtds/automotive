# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        api
# @Author:      philosophy
# @Created:     2022/02/19 - 22:24
# --------------------------------------------------------
from abc import ABCMeta, abstractmethod
from concurrent.futures import ThreadPoolExecutor, ALL_COMPLETED, wait
from enum import Enum, unique
from time import sleep
from typing import Tuple, Any, List, Optional

from .message import Message
from ..logger import logger
from ..checker import check_connect, can_tips

dlc = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    12: 9,
    16: 10,
    20: 11,
    24: 12,
    32: 13,
    48: 14,
    64: 15
}


@unique
class BaudRateEnum(Enum):
    """
    CAN传输速率

    目前支持HIGH、LOW
    """
    # 高速CAN
    HIGH = 500
    # 低速CAN
    LOW = 125
    # 数据仲裁速率
    DATA = 2000

    @staticmethod
    def from_value(type_: int):
        for key, item in BaudRateEnum.__members__.items():
            if type_ == item.value:
                return item
        raise ValueError(f"{type_} can not be found in BaudRateEnum")


@unique
class CanBoxDeviceEnum(Enum):
    """
    CAN盒子的类型，目前支持

    PEAKCAN、USBCAN、CANALYST
    """
    # PCAN
    PEAKCAN = "PEAKCAN", False
    # USB CAN
    USBCAN = "USBCAN", False
    # CAN分析仪
    CANALYST = "CANALYST", False
    # 同星
    TSMASTER = "TSMASTER", True
    # 周立功
    ZLG = "ZLG", True

    @staticmethod
    def from_name(type_: str):
        for key, item in CanBoxDeviceEnum.__members__.items():
            if type_.upper() == item.value[0]:
                return item
        raise ValueError(f"{type_} can not be found in CanBoxDeviceEnum")


class BaseCanDevice(metaclass=ABCMeta):

    def __init__(self):
        self._dlc = dlc
        self._is_open = False

    @property
    def is_open(self) -> bool:
        return self._is_open

    @abstractmethod
    def open_device(self, baud_rate: BaudRateEnum = BaudRateEnum.HIGH, data_rate: BaudRateEnum = BaudRateEnum.DATA,
                    channel: int = 1):
        """
        打开CAN设备
        :param channel: 通道，默认选择为1

        :param data_rate: 速率， 默认2M， 仅CANFD有用

        :param baud_rate: 速率，目前只支持500Kbps的高速CAN和125Kbps的低速CAN
        """
        pass

    @abstractmethod
    def close_device(self):
        """
        关闭CAN设备
        """
        pass

    @abstractmethod
    def transmit(self, message: Message):
        """
        发送CAN消息
        :param message: CAN消息
        """
        pass

    @abstractmethod
    def receive(self) -> Tuple[int, Any]:
        """
        接收CAN消息
        :return: message CAN消息
        """
        pass


class BaseCanBus(metaclass=ABCMeta):
    def __init__(self, baud_rate: BaudRateEnum = BaudRateEnum.HIGH, data_rate: BaudRateEnum = BaudRateEnum.DATA,
                 channel_index: int = 1, can_fd: bool = False, max_workers: int = 300):
        # baud_rate波特率，
        self._baud_rate = baud_rate
        # data_rate波特率， 仅canfd有用
        self._data_rate = data_rate
        # 通道
        self._channel_index = channel_index
        # CAN FD
        self._can_fd = can_fd
        # 最大线程数
        self._max_workers = max_workers
        # 保存接受数据帧的字典，用于接收
        self._receive_messages = dict()
        # 保存发送数据帧的字典，用于发送
        self._send_messages = dict()
        # 保存发送的事件信号的字典，用于发送
        self._event_send_messages = dict()
        # 用于存放接收到的数据
        self._stack = []
        # 周期性信号
        self._cycle = "Cycle"
        # 事件性信号
        self._event = "Event"
        # 周期事件性信号
        self._cycle_event = "Cycle and Event"
        # 线程池句柄
        self._thread_pool = ThreadPoolExecutor(max_workers=self._max_workers)
        # 是否需要接收，用于线程关闭
        self._need_receive = True
        # 是否需要一直发送
        self._need_transmit = True
        # 发送线程
        self._transmit_thread = []
        # 接收线程
        self._receive_thread = []
        # 事件信号线程
        self._event_thread = dict()
        # dlc对应关系
        self._dlc = dlc
        # can实例化的对象
        self._can = None

    @property
    def can_device(self) -> BaseCanDevice:
        return self._can

    @property
    def thread_pool(self) -> ThreadPoolExecutor:
        return self._thread_pool

    def _get_dlc_length(self, dlc_length: int) -> int:
        for key, value in self._dlc.items():
            if dlc_length == value:
                return key
        raise RuntimeError(f"dlc {dlc} not support, only support {self._dlc.keys()}")

    def __transmit(self, can: BaseCanDevice, message: Message, cycle_time: float):
        """
        CAN发送帧函数，在线程中执行。

        :param can can设备实例化

        :param message: message
        """
        logger.trace(f"cycle_time = {cycle_time}")
        msg_id = message.msg_id
        while can.is_open and not message.stop_flag and self._need_transmit:
            logger.debug(f"send msg {hex(msg_id)} and cycle time is {message.cycle_time}")
            try:
                can.transmit(message)
            except RuntimeError as e:
                logger.trace(f"some issue found, error is {e}")
            # 循环发送的等待周期
            sleep(cycle_time)

    def __cycle_msg(self, can: BaseCanDevice, message: Message):
        """
        发送周期性型号

        :param can can设备实例化

        :param message: message的集合对象
        """
        msg_id = message.msg_id
        # msg_id不在发送队列中
        condition1 = msg_id not in self._send_messages
        # msg_id在发送队列中，且stop_flag为真，即停止发送了得
        condition2 = msg_id in self._send_messages and self._send_messages[msg_id].stop_flag
        logger.debug(f"condition1[{condition1}] and condition2 = [{condition2}]")
        if condition1 or condition2:
            # 周期信号
            self._send_messages[msg_id] = message
            data = message.data
            hex_msg_id = hex(msg_id)
            cycle_time = message.cycle_time / 1000.0
            message.stop_flag = False
            # 周期性发送
            logger.info(f"****** Transmit [Cycle] {hex_msg_id} : {list(map(lambda x: hex(x), data))}"
                        f"Circle time is {message.cycle_time}ms ******")
            task = self._thread_pool.submit(self.__transmit, can, message, cycle_time)
            self._transmit_thread.append(task)
        else:
            # 周期事件信号，当周期信号发送的时候，只在变化data的时候会进行快速发送消息
            if message.msg_send_type == self._cycle_event:
                # 暂停已发送的消息
                self.stop_transmit(msg_id)
                self._send_messages[msg_id].data = message.data
                self.__event(can, message)
                # 发送完成了周期性事件信号，恢复信号发送
                self.resume_transmit(msg_id)
            else:
                # 已经在里面了，所以修改data值而已
                self._send_messages[msg_id].data = message.data

    def __event_transmit(self, can: BaseCanDevice, msg_id: int, cycle_time: float):
        """
        事件信号发送线程
        :return:
        """
        # 需要发送数据以及当前还有数据可以发送
        while self._need_transmit and msg_id in self._event_send_messages and len(
                self._event_send_messages[msg_id]) > 0:
            message = self._event_send_messages[msg_id].pop(0)
            can.transmit(message)
            logger.debug(f"****** Transmit [Event] {msg_id} : {list(map(lambda x: hex(x), message.data))}"
                         f"Event Cycle time [{message.cycle_time_fast}]")
            sleep(cycle_time)

    def __event(self, can: BaseCanDevice, message: Message):
        """
        发送事件信号
        :param can can设备实例化
        :param message: message的集合对象
        """
        msg_id = message.msg_id
        cycle_time = message.cycle_time_fast / 1000.0
        # 事件信号
        event_times = message.cycle_time_fast_times if message.cycle_time_fast_times > 0 else 1
        # 构建消息列表
        messages = []
        for i in range(event_times):
            messages.append(message)
        # 第一次发送
        if msg_id not in self._event_send_messages:
            self._event_send_messages[msg_id] = messages
            # 第一次发送，所以需要新开线程
            self._event_thread[msg_id] = self._thread_pool.submit(self.__event_transmit, can, msg_id, cycle_time)
        else:
            self._event_send_messages[msg_id] += messages
            # 判断消息是否发送完成，若发送完成则需要新开线程，否则继续使用老的线程发送
            if self._event_thread[msg_id].done():
                self._event_thread[msg_id] = self._thread_pool.submit(self.__event_transmit, can, msg_id, cycle_time)

    def _open_can(self):
        """
        对CAN设备进行打开、初始化等操作，并同时开启设备的帧接收线程。
        """
        # 线程池句柄
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=self._max_workers)
        # 开启设备的接收线程
        self._need_receive = True
        # 开启设备的发送线程
        self._need_transmit = True
        # 打开设备，并初始化设备
        self._can.open_device(baud_rate=self._baud_rate, data_rate=self._data_rate, channel=self._channel_index)

    @abstractmethod
    def open_can(self):
        """
        对CAN设备进行打开、初始化等操作，并同时开启设备的帧接收线程。
        """
        pass

    def close_can(self):
        """
            关闭USB CAN设备。
        """
        self._need_transmit = False
        logger.trace("wait _transmit_thread close")
        wait(self._transmit_thread, return_when=ALL_COMPLETED)
        self._need_receive = False
        logger.trace("wait _receive_thread close")
        wait(self._receive_thread, return_when=ALL_COMPLETED)
        logger.trace("wait _event_thread close")
        wait(self._event_thread.values(), return_when=ALL_COMPLETED)
        if self._thread_pool:
            logger.info("shutdown thread pool")
            self._thread_pool.shutdown()
        logger.trace("_send_messages clear")
        self._send_messages.clear()
        self._thread_pool = None
        logger.trace("close_device")
        self._can.close_device()

    @check_connect("_can", can_tips, is_bus=True)
    def transmit(self, message: Message):
        """
        发送CAN帧函数。

        :param message: message对象
        """
        cycle_time = message.cycle_time
        logger.debug(f"message send type is {message.msg_send_type}")
        if message.msg_send_type == self._cycle or cycle_time > 0:
            logger.debug("cycle send message")
            # 周期信号
            self.__cycle_msg(self._can, message)
        elif message.msg_send_type == self._event:
            logger.debug("event send message")
            # 事件信号
            self.__event(self._can, message)
        elif message.msg_send_type == self._cycle_event:
            logger.debug("cycle&event send message")
            # 周期事件信号
            self.__cycle_msg(self._can, message)

    @check_connect("_can", can_tips, is_bus=True)
    def transmit_one(self, message: Message):
        """
        发送CAN帧函数。

        :param message: message对象
        """
        self._can.transmit(message)

    @check_connect("_can", can_tips, is_bus=True)
    def stop_transmit(self, message_id: int):
        """
        停止某一帧CAN数据的发送。(当message_id为None时候停止所有发送的CAN数据)

        :param message_id: 停止发送的Message的ID
        """
        """
        停止某一帧CAN数据的发送。(当message_id为None时候停止所有发送的CAN数据)

        :param msg_id: 停止发送的Message的ID
        """
        logger.trace(f"send message list size is {len(self._send_messages)}")
        if message_id:
            logger.trace(f"try to stop message {hex(message_id)}")
            if message_id in self._send_messages:
                logger.info(f"Message <{hex(message_id)}> is stop to send.")
                self._send_messages[message_id].stop_flag = True
                # self._send_messages[message_id].pause_flag = True
            else:
                logger.error(f"Please check message id, Message <{hex(message_id)}> is not contain.")
        else:
            logger.trace(f"try to stop all messages")
            for key, item in self._send_messages.items():
                logger.info(f"Message <{hex(key)}> is stop to send.")
                item.stop_flag = True
                # item.pause_flag = True

    @check_connect("_can", can_tips, is_bus=True)
    def resume_transmit(self, message_id: int):
        """
       恢复某一帧数据的发送函数。

       :param message_id:停止发送的Message的ID
       """
        if message_id:
            logger.trace(f"try to resume message {hex(message_id)}")
            if message_id in self._send_messages:
                logger.info(f"Message <{hex(message_id)}> is resume to send.")
                message = self._send_messages[message_id]
                # message.stop_flag = False
                self.transmit(message)
            else:
                logger.error(f"Please check message id, Message <{hex(message_id)}> is not contain.")
        else:
            logger.trace(f"try to resume all messages")
            for key, item in self._send_messages.items():
                logger.info(f"Message <{hex(key)}> is resume to send.")
                # 当发现这个msg是停止的时候就恢复发送
                if item.stop_flag:
                    # item.stop_flag = False
                    self.transmit(item)

    @check_connect("_can", can_tips, is_bus=True)
    def receive(self, message_id: int) -> Message:
        """
        接收函数。此函数从指定的设备CAN通道的接收缓冲区中读取数据。

        :param message_id: 接收所需Message的ID

        :return: Message对象
        """
        if message_id in self._receive_messages:
            return self._receive_messages[message_id]
        else:
            raise RuntimeError(f"message_id {message_id} not receive")

    @check_connect("_can", can_tips, is_bus=True)
    def get_stack(self) -> List[Message]:
        """
        获取CAN的stack
        """
        return self._stack

    @check_connect("_can", can_tips, is_bus=True)
    def clear_stack_data(self):
        """
        清除栈数据
        """
        self._stack.clear()


class Singleton(type):
    """
    单例方法，所有的类要使用则需要继承该类

    目前CANService使用到了单例方法
    """

    def __init__(cls, what, bases: Optional[Any] = None, dict_: Optional[Any] = None):
        """
        初始化Type类
        :param what: 类名
        :param bases: 类所继承的基类
        :param dict_: 类的属性
        """
        super().__init__(what, bases, dict_)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance
