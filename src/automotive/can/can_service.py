# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        can_service
# @Author:      philosophy
# @Created:     2022/02/19 - 22:54
# --------------------------------------------------------
import time
import random
import copy
from time import sleep
from typing import Tuple, Union, List, Any, Dict, Optional

from .message import Message, get_message, MessageType
from .abstract_class import BaseCanBus, CanBoxDeviceEnum, BaudRateEnum, Singleton
from ..logger import logger

FilterNode = Union[str, Union[Tuple[str, ...], List[str]]]
MessageIdentity = Union[int, str]


def __get_can_bus(can_box_device: CanBoxDeviceEnum, baud_rate: BaudRateEnum, data_rate: BaudRateEnum,
                  channel_index: int, can_fd: bool, max_workers: int) -> BaseCanBus:
    if can_box_device == CanBoxDeviceEnum.PEAKCAN:
        logger.debug("use pcan")
        from .pcan_bus import PCanBus
        return PCanBus(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index, can_fd=can_fd,
                       max_workers=max_workers)
    elif can_box_device == CanBoxDeviceEnum.TSMASTER:
        logger.debug("use tsmaster")
        from .tsmaster_bus import TsMasterCanBus
        return TsMasterCanBus(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index, can_fd=can_fd,
                              max_workers=max_workers)
    elif can_box_device == CanBoxDeviceEnum.ZLGUSBCAN:
        logger.debug("use zlg")
        from .zlg_bus import ZlgCanBus
        return ZlgCanBus(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index, can_fd=can_fd,
                         max_workers=max_workers)
    elif can_box_device == CanBoxDeviceEnum.CANALYST or can_box_device == CanBoxDeviceEnum.USBCAN:
        logger.debug("use usbcan")
        from .usbcan_bus import UsbCanBus
        return UsbCanBus(can_box_device, baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index,
                         can_fd=can_fd, max_workers=max_workers)
    else:
        raise RuntimeError(f"{can_box_device.value} not support")


def get_can_box_device(can_box_device: CanBoxDeviceEnum, baud_rate: BaudRateEnum, data_rate: BaudRateEnum,
                       channel_index: int, can_fd: bool, max_workers: int) -> Tuple[CanBoxDeviceEnum, BaseCanBus]:
    """
    获取can盒子的类型， 依次从PCan找到CANALYST然后到USBCAN
    :return: can盒类型
    """
    if can_box_device:
        return can_box_device, __get_can_bus(can_box_device, baud_rate, data_rate, channel_index, can_fd, max_workers)
    else:
        for key, value in CanBoxDeviceEnum.__members__.items():
            name, type_ = value.value
            if can_fd is True and type_ is True:
                logger.info(f"try to open {key}")
                can = __get_can_bus(value, baud_rate, data_rate, channel_index, can_fd, max_workers)
                try:
                    can.open_can()
                    sleep(1)
                    can.close_can()
                    return value, __get_can_bus(value, baud_rate, data_rate, channel_index, can_fd, max_workers)
                except RuntimeError:
                    logger.debug(f"open {name} failed")
            elif can_fd is False:
                logger.info(f"try to open {key}")
                can = __get_can_bus(value, baud_rate, data_rate, channel_index, can_fd, max_workers)
                try:
                    can.open_can()
                    sleep(1)
                    can.close_can()
                    return value, __get_can_bus(value, baud_rate, data_rate, channel_index, can_fd, max_workers)
                except RuntimeError:
                    logger.debug(f"open {name} failed")
        raise RuntimeError("No device found, is can box connected")


class Can(metaclass=Singleton):
    """
    CAN设备操作的父类，实现CAN的最基本的操作， 如打开、关闭设备, 传输、接收CAN消息，停止传输CAN消息，查看CAN设备打开状态等
    """

    def __init__(self,
                 can_box_device: Union[CanBoxDeviceEnum, str, None] = None,
                 baud_rate: Union[BaudRateEnum, int] = BaudRateEnum.HIGH,
                 data_rate: Union[BaudRateEnum, int] = BaudRateEnum.DATA,
                 channel_index: int = 1,
                 can_fd: bool = False,
                 max_workers: int = 300):
        if isinstance(can_box_device, str):
            can_box_device = CanBoxDeviceEnum.from_name(can_box_device)
        if isinstance(baud_rate, int):
            baud_rate = BaudRateEnum.from_value(baud_rate)
        if isinstance(data_rate, int):
            data_rate = BaudRateEnum.from_value(data_rate)
        self._can_box_device, self._can = get_can_box_device(can_box_device, baud_rate, data_rate, channel_index,
                                                             can_fd, max_workers)

    @property
    def can_box_device(self) -> CanBoxDeviceEnum:
        return self._can_box_device

    @property
    def can_bus(self) -> BaseCanBus:
        return self._can

    def open_can(self):
        """
        对CAN设备进行打开、初始化等操作，并同时开启设备的帧接收线程。
        """
        self._can.open_can()

    def close_can(self):
        """
        关闭USB CAN设备。
        """
        self._can.close_can()

    def stop_transmit(self, message_id: int = None):
        """
        发送CAN帧函数。

        :param message_id: message对象
        """
        self._can.stop_transmit(message_id)

    def resume_transmit(self, message_id: int):
        """
        恢复某一帧数据的发送函数。

        :param message_id:停止发送的Message的ID
        """
        self._can.resume_transmit(message_id)

    def transmit(self, message: Message):
        """
        发送CAN消息帧

        :param message CAN消息帧，Message对象
        """
        self._can.transmit(message)

    def transmit_one(self, message: Message):
        """
        仅发一帧数据

        :param message:
        """
        self._can.transmit_one(message)

    def receive(self, message_id: int) -> Message:
        """
        接收CAN消息

        :param message_id: message的ID

        :return: Message对象
        """
        return self._can.receive(message_id)

    def clear_stack_data(self):
        """
        清除栈数据
        """
        self._can.clear_stack_data()

    def get_stack(self) -> List[Message]:
        """
        获取当前栈中所收到的消息

        :return:  栈中数据List<Message>
        """
        return self._can.get_stack()


class CANService(Can):
    """
    CAN的服务类，主要用于CAN信号的发送，接收等操作。

    参数can_box_device用于指定设备，默认为None，即会依次寻找PCan、Can分析仪以及UsbCan三个设备

    也可以指定某个设备。

    该类可以传入相关的Message消息后，实现自动解析相关的信息计算出一个Message的8 byte的数据值，无需人工计算相关的值。

    该类同时扩展了基础的CAN服务，实现了以下服务

    1、发送message(周期/事件/周期事件)

    2、发送设置好的8 byte数据， 或者根据设置的signal来发送数据

    3、接收message数据，或者接收message的signal数据

    4、判断message是否丢失、判断CAN总线是否丢失、判断signal是否有变化

    5、获取/清除CAN总线上收到的数据、分析CAN消息上的数据

    6、根据message(即矩阵表)随机发送can上消息

    PS: message矩阵表为解析DBC文件生成（该工具为另外一个工具)

    """

    def __init__(self,
                 messages: Union[str, MessageType],
                 encoding: str = "utf-8",
                 can_box_device: Union[CanBoxDeviceEnum, str, None] = None,
                 baud_rate: Union[BaudRateEnum, int] = BaudRateEnum.HIGH,
                 data_rate: Union[BaudRateEnum, int] = BaudRateEnum.DATA,
                 channel_index: int = 1,
                 can_fd: bool = False,
                 max_workers: int = 300):
        super().__init__(can_box_device, baud_rate, data_rate, channel_index, can_fd, max_workers)
        logger.debug(f"read message from file {messages}")
        self.__messages, self.__name_messages = get_message(messages, encoding=encoding)
        # 备份message, 可以作为初始值发送
        self.__backup_messages = copy.deepcopy(self.__messages)
        self.__backup_name_messages = copy.deepcopy(self.__name_messages)

    @property
    def name_messages(self) -> Dict[str, Any]:
        return self.__name_messages

    @property
    def messages(self) -> Dict[int, Any]:
        return self.__messages

    def __restore_default_message(self):
        """
        恢复初始的message值
        """
        self.__messages = copy.deepcopy(self.__backup_messages)
        self.__name_messages = copy.deepcopy(self.__backup_name_messages)

    def __set_message(self, msg_id: int, data: list) -> Message:
        """
        :param msg_id: 消息ID

        :param data: 数据

        :return: Message对象
        """
        msg = self.messages[msg_id]
        msg.data = data
        msg.update(False)
        return msg

    @staticmethod
    def __is_message_in_node(message: Message, filter_sender: FilterNode) -> bool:
        sender = message.sender.lower()
        if isinstance(filter_sender, str):
            return sender == filter_sender.lower()
        elif isinstance(filter_sender, (tuple, list)):
            for item in filter_sender:
                if sender == item.lower():
                    return True
            return False

    def __filter_messages(self,
                          filter_sender: Optional[FilterNode] = None,
                          filter_nm: bool = True,
                          filter_diag: bool = True) -> List[Message]:
        """
        根据条件过滤相应的消息帧

        :param filter_sender: 根据节点名称过滤

        :param filter_nm: 是否过滤网络管理帧

        :param filter_diag: 是否过滤诊断帧

        :return: 过滤后的消息
        """
        messages = []
        for msg_id, message in self.messages.items():
            if filter_sender:
                is_filter_sender = self.__is_message_in_node(message, filter_sender)
            else:
                is_filter_sender = False
            is_diag_message = filter_nm and (message.diag_request or message.diag_response or message.diag_state)
            is_nm_message = filter_diag and message.nm_message
            if not (is_filter_sender or is_diag_message or is_nm_message):
                messages.append(message)
        return messages

    def __send_message(self,
                       message: Message,
                       default_message: Optional[Dict[str, str]] = None,
                       is_random_value: bool = False):
        """
        计算值并发送消息

        :param message: 消息

        :param default_message: 默认发送的消息
        """
        msg_id = message.msg_id
        if is_random_value:
            if default_message and msg_id in default_message:
                for sig_name, sig in message.signals.items():
                    if sig_name in default_message[msg_id]:
                        sig.value = default_message[msg_id][sig_name]
                    else:
                        max_value = 2 ** sig.bit_length - 1
                        value = random.randint(0, max_value)
                        logger.trace(f"value is [{value}]")
                        sig.value = value
            else:
                for sig_name, sig in message.signals.items():
                    max_value = 2 ** sig.bit_length - 1
                    value = random.randint(0, max_value)
                    logger.trace(f"value is [{value}]")
                    sig.value = value
        logger.trace(f"sender is {message.sender}")
        self.send_can_message(message)
        # # 避免错误发生后不再发送数据，容错处理
        # try:
        #     logger.trace(f"sender is {message.sender}")
        #     self.send_can_message(message)
        # except RuntimeError as e:
        #     logger.error(f"transmit message {hex(msg_id)} failed, error is {e}")

    def __send_messages(self,
                        messages: List[Message],
                        interval: float = 0,
                        default_message: Optional[Dict[str, str]] = None,
                        is_random_value: bool = False):
        for message in messages:
            self.__send_message(message, default_message, is_random_value)
        if interval > 0:
            sleep(interval)

    def __get_msg_id_from_signal_name(self, signal_name: str) -> int:
        for msg_name, msg in self.messages.items():
            if signal_name in msg.signals:
                return msg.msg_id
        raise RuntimeError(f"{signal_name} can not be found in messages")

    def send_can_message_by_id_or_name(self, msg: MessageIdentity):
        """
        据矩阵表中定义的Messages，通过msg ID或者name来发送message到网络中

        该方法仅发送Message消息，但不会改变Message的值，如需改变值，请使用send_can_signal_message方法

        :param msg： msg的名字或者id
        """
        if isinstance(msg, int):
            send_msg = self.messages[msg]
        elif isinstance(msg, str):
            send_msg = self.name_messages[msg]
        else:
            raise RuntimeError(f"msg only support str or int, but now is {msg}")
        self.send_can_message(send_msg, False)

    def send_can_signal_message(self, msg: MessageIdentity, signal: Dict[str, int]):
        """
        根据矩阵表中定义的Messages，来设置并发送message。

        tips：不支持8byte数据发送，如果是8Byte数据请使用send_can_message来发送

        :param msg: msg的名字或者id

        :param signal: 需要修改的信号，其中key是信号名字，value是物理值（如车速50)

            如： {"signal_name1": 0x1, "signal_name2": 0x2}
        """
        if isinstance(msg, str):
            msg_id = self.name_messages[msg]
        elif isinstance(msg, int):
            msg_id = msg
        else:
            raise RuntimeError(f"msg only support msg id or msg name but current value is {msg}")
        set_message = self.messages[msg_id]
        for name, value in signal.items():
            set_signal = set_message.signals[name]
            set_signal.physical_value = value
        set_message.check_message()
        self.send_can_message_by_id_or_name(msg_id)

    def send_can_message(self, send_msg: Message, type_: bool = False):
        """
        直接发送的Message对象数据，可以选择8byte数据发送和signals数据发送两种方式，默认使用signals方式构建数据

        :param send_msg: Message对象

        :param type_: 发送类型（默认使用Signals方式)

            True： 8byte数据发送

            False: signals方式发送
        """
        send_msg.check_message(type_)
        if not type_:
            logger.debug("now update message")
            send_msg.update(True)
        logger.debug(f"msg Id {hex(send_msg.msg_id)}, msg data is {list(map(lambda x: hex(x), send_msg.data))}")
        self.transmit(send_msg)

    def receive_can_message(self, message_id: int) -> Message:
        """
        接收在CAN上收到的Message消息，当能够在内置的messages对象中查询到则能够查询到具体的signals的值，否则只能查询到8byte数据

        :param message_id: message id值

        :return: Message对象
        """
        receive_msg = self.receive(message_id)
        try:
            # 如果能在messages对象中查询到相关内容，更新一下value值
            json_msg = self.messages[receive_msg.msg_id]
            json_msg.data = receive_msg.data
            json_msg.update(False)
            return json_msg
        except KeyError:
            return receive_msg

    def receive_can_message_signal_value(self, message_id: int, signal_name: str) -> float:
        """
        接收CAN上收到的消息并返回指定的signal的值， 如果Message不是在messages中已定义的，则会抛出异常

        :param message_id: message id值

        :param signal_name: 信号的名称

        :return: 查到的指定信号的物理值
        """
        return self.receive_can_message(message_id).signals[signal_name].physical_value

    def is_lost_message(self,
                        msg_id: int,
                        cycle_time: int,
                        continue_time: int = 5,
                        lost_period: Optional[int] = None,
                        bus_time: Optional[int] = None) -> bool:
        """
        判断message是否丢失

        判断规则：

        1、总线是否丢失

        2、最后两帧收到的消息间隔时间大于信号周期间隔时间且收到的消息小于应该收到的消息去掉信号丢失周期应该收到的消息数量

        :param msg_id: message id值

        :param lost_period: 信号丢失周期（默认为10个周期)

        :param continue_time: 检测时间（当不为空的时候，会清空数据并等待time ms，然后再检测数据)

        :param cycle_time: 信号周期 单位ms

        :param bus_time: 总线丢失检测时间,默认不检测
        """
        # 先判断是否总线丢失，如果总线丢失则表示信号丢失
        if bus_time:
            logger.info(f"judge bus status")
            if self.is_can_bus_lost(bus_time):
                return True
        logger.debug(f"sleep {continue_time}")
        # 清空栈数据，继续接收数据
        self.clear_stack_data()
        time.sleep(continue_time)
        stack = self._can.get_stack()
        logger.debug(f"stack size is {len(stack)}")
        # 过滤掉没有用的数据
        msg_stack_list = list(filter(lambda x: x.msg_id == msg_id, stack))
        msg_stack_size = len(msg_stack_list)
        logger.debug(f"msg_stack_size is {msg_stack_size}")
        # 计算continue_time时间内应该受到的帧数量
        receive_msg_size = (continue_time * 1000) / cycle_time
        logger.debug(f"receive_msg_size is {receive_msg_size}")
        if lost_period:
            logger.debug(f"lost_period exist")
            # 确保至少收到两个以上的信号
            if msg_stack_size < 2:
                return True
            else:
                pass_time = (int(msg_stack_list[-1].time_stamp, 16) - int(msg_stack_list[-2].time_stamp, 16)) / 1000
                judge_time = cycle_time * lost_period
                logger.info(f"pass time is {pass_time} and judge time is {judge_time}")
                # 最后两帧的间隔时间大于信号周期间隔时间且收到的消息小于应该收到的消息去掉信号丢失周期应该收到的消息
                max_lost_receive_msg_size = receive_msg_size - (lost_period * 1000) / cycle_time
                logger.info(f"msg_stack_size is {msg_stack_size} and max_size is {max_lost_receive_msg_size}")
                return pass_time > judge_time and msg_stack_size < max_lost_receive_msg_size
        else:
            logger.info(f"need receive msg size [{receive_msg_size}] and actual receive size is [{msg_stack_size}]")
            return msg_stack_size < receive_msg_size

    def is_can_bus_lost(self, continue_time: int = 5) -> bool:
        """
        can总线是否数据丢失，如果检测周期内有一帧can信号表示can网络没有中断

        :param continue_time: 清空数据，10s内收不到任何的CAN消息表示CAN总线丢失
        """
        # 清空栈数据
        self.clear_stack_data()
        time.sleep(continue_time)
        return len(self._can.get_stack()) == 0

    @staticmethod
    def is_msg_value_changed(stack: List[Message], msg_id: int) -> bool:
        """
        检测某个msg是否有变化，只能检测到整个8byte数据是否有变化

        :param stack: 记录下来的CAN消息

        :param msg_id: 信号ID

        :return:
            True: 有变化

            False: 没有变化
        """
        # 过滤掉没有用的数据
        data_list = list(filter(lambda x: x.msg_id == msg_id, stack))
        duplicate = set()
        for message in data_list:
            data = message.data
            duplicate.add(data)
        return len(duplicate) > 1

    @staticmethod
    def is_signal_value_changed(stack: List[Message], msg_id: int, signal_name: str) -> bool:
        """
        检测某个msg中某个signal是否有变化

        :param stack: 记录下来的CAN消息

        :param msg_id: 信号ID

        :param signal_name: 信号名称

        :return:
            True: 有变化

            False: 没有变化
        """
        # 过滤掉没有用的数据
        data_list = list(filter(lambda x: x.msg_id == msg_id, stack))
        duplicate = set()
        for message in data_list:
            signal = message.signals[signal_name]
            duplicate.add(signal.value)
        return len(duplicate) > 1

    def get_receive_signal_values(self,
                                  stack: List[Message],
                                  signal_name: str,
                                  msg_id: Optional[str] = None) -> List[int]:
        """
        所有曾经出现的信号值
        :param stack:
        :param msg_id:
        :param signal_name:
        :return:
        """
        if msg_id is None:
            msg_id = self.__get_msg_id_from_signal_name(signal_name)
        result = []
        filter_messages = list(filter(lambda x: x.msg_id == msg_id, stack))
        for msg in filter_messages:
            message = self.__set_message(msg.msg_id, msg.data)
            if signal_name not in message.signals:
                raise RuntimeError(f"{signal_name} is not in {msg_id}")
            else:
                signal = message.signals[signal_name]
                if signal.physical_value not in result:
                    result.append(signal.physical_value)
        return result

    def check_signal_value(self,
                           stack: List[Message],
                           signal_name: str,
                           expect_value: int,
                           msg_id: Optional[int] = None,
                           count: Optional[int] = None,
                           exact: bool = True):
        """
        检查signal的值是否符合要求

        :param exact: 是否精确对比

        :param msg_id: msg id

        :param signal_name:  sig name

        :param expect_value: expect value

        :param count: 检查数量

        :param stack: 栈中消息
        """
        if msg_id is None:
            msg_id = self.__get_msg_id_from_signal_name(signal_name)
        if count:
            # 过滤需要的msg
            filter_messages = list(filter(lambda x: x.msg_id == msg_id, stack))
            logger.debug(f"filter messages length is {len(filter_messages)}")
            msg_count = 0
            for msg in filter_messages:
                logger.debug(f"msg data = {msg.data}")
                # 此时的msg只有data，需要调用方法更新内容
                message = self.__set_message(msg.msg_id, msg.data)
                actual_value = message.signals[signal_name].physical_value
                logger.debug(f"actual_value = {actual_value}")
                if actual_value == expect_value:
                    msg_count += 1
            logger.info(f"except count is {count}, actual count = {msg_count}")
            if exact:
                return msg_count == count
            else:
                return msg_count >= count
        else:
            # 直接读取can上的最后的值
            actual_value = self.receive_can_message_signal_value(msg_id, signal_name)
            logger.info(f"current value is {actual_value}, expect value is {expect_value}")
            return expect_value == actual_value

    def send_random(self,
                    filter_sender: Optional[FilterNode] = None,
                    cycle_time: Optional[int] = None, interval: float = 0.1,
                    default_message: Optional[Dict[str, str]] = None,
                    filter_nm: bool = True,
                    filter_diag: bool = True):
        """
        随机发送信号

        1、不发送诊断帧和网络管理帧

        2、信号的值随机设置

        3、需要过滤指定的发送者

        :param default_message: 固定要发送的信号 {0x152: {"aaa": 0x1, "bbb": 0xc}, 0x119: {"ccc": 0x1, "ddd": 0x2}}

        :param filter_sender: 过滤发送者，如HU。支持单个或者多个节点

        :param cycle_time: 循环次数

        :param interval: 每轮信号值改变的间隔时间，默认是0.1秒

        :param filter_nm: 是否过滤网络管理报文

        :param filter_diag: 是否过滤诊断报文
        """
        messages = self.__filter_messages(filter_sender, filter_nm, filter_diag)
        if cycle_time:
            for i in range(cycle_time):
                logger.info(f"The {i + 1} time set random value")
                self.__send_messages(messages, interval, default_message, True)
        else:
            while True:
                self.__send_messages(messages, interval, default_message, True)

    def send_messages(self, filter_sender: Optional[FilterNode] = None):
        """
        发送除了filter_sender之外的所有信号，该方法用于发送出测试对象之外的所有信号

        :param filter_sender: 过滤发送者，如HU。支持单个或者多个节点
        """
        messages = self.__filter_messages(filter_sender)
        self.__send_messages(messages)

    def send_default_messages(self, filter_sender: Optional[FilterNode] = None):
        """
        发送除了node_name之外的所有信号的默认数据，该方法用于发送出测试对象之外的所有信号

        :param filter_sender: 测试对象节点名称
        """
        self.__restore_default_message()
        self.send_messages(filter_sender)
