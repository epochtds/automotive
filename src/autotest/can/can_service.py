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
        from autotest.can.peakcan.pcan_bus import PCanBus
        return PCanBus(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index, can_fd=can_fd,
                       max_workers=max_workers)
    elif can_box_device == CanBoxDeviceEnum.TSMASTER:
        logger.debug("use tsmaster")
        from autotest.can.tsmaster.tsmaster_bus import TsMasterCanBus
        return TsMasterCanBus(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index, can_fd=can_fd,
                              max_workers=max_workers)
    elif can_box_device == CanBoxDeviceEnum.ZLGUSBCAN:
        logger.debug("use zlg")
        from autotest.can.zlg.zlg_bus import ZlgCanBus
        return ZlgCanBus(baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index, can_fd=can_fd,
                         max_workers=max_workers)
    elif can_box_device == CanBoxDeviceEnum.CANALYST or can_box_device == CanBoxDeviceEnum.USBCAN:
        logger.debug("use usbcan")
        from autotest.can.usbcan.usbcan_bus import UsbCanBus
        return UsbCanBus(can_box_device, baud_rate=baud_rate, data_rate=data_rate, channel_index=channel_index,
                         can_fd=can_fd, max_workers=max_workers)
    else:
        raise RuntimeError(f"{can_box_device.value} not support")


def get_can_box_device(can_box_device: CanBoxDeviceEnum, baud_rate: BaudRateEnum, data_rate: BaudRateEnum,
                       channel_index: int, can_fd: bool, max_workers: int) -> Tuple[CanBoxDeviceEnum, BaseCanBus]:
    """
    ??????can?????????????????? ?????????PCan??????CANALYST?????????USBCAN
    :return: can?????????
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


class CanBus(metaclass=Singleton):
    """
    CAN??????????????????????????????CAN???????????????????????? ????????????????????????, ???????????????CAN?????????????????????CAN???????????????CAN?????????????????????
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
        ???CAN????????????????????????????????????????????????????????????????????????????????????
        """
        self._can.open_can()

    def close_can(self):
        """
        ??????USB CAN?????????
        """
        self._can.close_can()

    def stop_transmit(self, message_id: int = None):
        """
        ??????CAN????????????

        :param message_id: message??????
        """
        self._can.stop_transmit(message_id)

    def resume_transmit(self, message_id: int):
        """
        ???????????????????????????????????????

        :param message_id:???????????????Message???ID
        """
        self._can.resume_transmit(message_id)

    def transmit(self, message: Message):
        """
        ??????CAN?????????

        :param message CAN????????????Message??????
        """
        self._can.transmit(message)

    def transmit_one(self, message: Message):
        """
        ??????????????????

        :param message:
        """
        self._can.transmit_one(message)

    def receive(self, message_id: int) -> Message:
        """
        ??????CAN??????

        :param message_id: message???ID

        :return: Message??????
        """
        return self._can.receive(message_id)

    def clear_stack_data(self):
        """
        ???????????????
        """
        self._can.clear_stack_data()

    def get_stack(self) -> List[Message]:
        """
        ????????????????????????????????????

        :return:  ????????????List<Message>
        """
        return self._can.get_stack()


class CanService(CanBus):
    """
    CAN???????????????????????????CAN????????????????????????????????????

    ??????can_box_device??????????????????????????????None?????????????????????PCan???Can???????????????UsbCan????????????

    ??????????????????????????????

    ???????????????????????????Message????????????????????????????????????????????????????????????Message???8 byte????????????????????????????????????????????????

    ??????????????????????????????CAN??????????????????????????????

    1?????????message(??????/??????/????????????)

    2?????????????????????8 byte????????? ?????????????????????signal???????????????

    3?????????message?????????????????????message???signal??????

    4?????????message?????????????????????CAN???????????????????????????signal???????????????

    5?????????/??????CAN?????????????????????????????????CAN??????????????????

    6?????????message(????????????)????????????can?????????

    PS: message??????????????????DBC?????????????????????????????????????????????)

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
        # ??????message, ???????????????????????????
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
        ???????????????message???
        """
        self.__messages = copy.deepcopy(self.__backup_messages)
        self.__name_messages = copy.deepcopy(self.__backup_name_messages)

    def __set_message(self, msg_id: int, data: list) -> Message:
        """
        :param msg_id: ??????ID

        :param data: ??????

        :return: Message??????
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
        ????????????????????????????????????

        :param filter_sender: ????????????????????????

        :param filter_nm: ???????????????????????????

        :param filter_diag: ?????????????????????

        :return: ??????????????????
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
        ????????????????????????

        :param message: ??????

        :param default_message: ?????????????????????
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
        # # ??????????????????????????????????????????????????????
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
        ????????????????????????Messages?????????msg ID??????name?????????message????????????

        ??????????????????Message????????????????????????Message????????????????????????????????????send_can_signal_message??????

        :param msg??? msg???????????????id
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
        ???????????????????????????Messages?????????????????????message???

        tips????????????8byte????????????????????????8Byte???????????????send_can_message?????????

        :param msg: msg???????????????id

        :param signal: ??????????????????????????????key??????????????????value????????????????????????50)

            ?????? {"signal_name1": 0x1, "signal_name2": 0x2}
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
        ???????????????Message???????????????????????????8byte???????????????signals???????????????????????????????????????signals??????????????????

        :param send_msg: Message??????

        :param type_: ???????????????????????????Signals??????)

            True??? 8byte????????????

            False: signals????????????
        """
        send_msg.check_message(type_)
        if not type_:
            logger.debug("now update message")
            send_msg.update(True)
        logger.debug(f"msg Id {hex(send_msg.msg_id)}, msg data is {list(map(lambda x: hex(x), send_msg.data))}")
        self.transmit(send_msg)

    def receive_can_message(self, message_id: int) -> Message:
        """
        ?????????CAN????????????Message??????????????????????????????messages?????????????????????????????????????????????signals??????????????????????????????8byte??????

        :param message_id: message id???

        :return: Message??????
        """
        receive_msg = self.receive(message_id)
        try:
            # ????????????messages?????????????????????????????????????????????value???
            json_msg = self.messages[receive_msg.msg_id]
            json_msg.data = receive_msg.data
            json_msg.update(False)
            return json_msg
        except KeyError:
            return receive_msg

    def receive_can_message_signal_value(self, message_id: int, signal_name: str) -> float:
        """
        ??????CAN????????????????????????????????????signal????????? ??????Message?????????messages????????????????????????????????????

        :param message_id: message id???

        :param signal_name: ???????????????

        :return: ?????????????????????????????????
        """
        return self.receive_can_message(message_id).signals[signal_name].physical_value

    def is_lost_message(self,
                        msg_id: int,
                        cycle_time: int,
                        continue_time: int = 5,
                        lost_period: Optional[int] = None,
                        bus_time: Optional[int] = None) -> bool:
        """
        ??????message????????????

        ???????????????

        1?????????????????????

        2????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

        :param msg_id: message id???

        :param lost_period: ??????????????????????????????10?????????)

        :param continue_time: ???????????????????????????????????????????????????????????????time ms????????????????????????)

        :param cycle_time: ???????????? ??????ms

        :param bus_time: ????????????????????????,???????????????
        """
        # ?????????????????????????????????????????????????????????????????????
        if bus_time:
            logger.info(f"judge bus status")
            if self.is_can_bus_lost(bus_time):
                return True
        logger.debug(f"sleep {continue_time}")
        # ????????????????????????????????????
        self.clear_stack_data()
        time.sleep(continue_time)
        stack = self._can.get_stack()
        logger.debug(f"stack size is {len(stack)}")
        # ???????????????????????????
        msg_stack_list = list(filter(lambda x: x.msg_id == msg_id, stack))
        msg_stack_size = len(msg_stack_list)
        logger.debug(f"msg_stack_size is {msg_stack_size}")
        # ??????continue_time?????????????????????????????????
        receive_msg_size = (continue_time * 1000) / cycle_time
        logger.debug(f"receive_msg_size is {receive_msg_size}")
        if lost_period:
            logger.debug(f"lost_period exist")
            # ???????????????????????????????????????
            if msg_stack_size < 2:
                return True
            else:
                pass_time = (int(msg_stack_list[-1].time_stamp, 16) - int(msg_stack_list[-2].time_stamp, 16)) / 1000
                judge_time = cycle_time * lost_period
                logger.info(f"pass time is {pass_time} and judge time is {judge_time}")
                # ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
                max_lost_receive_msg_size = receive_msg_size - (lost_period * 1000) / cycle_time
                logger.info(f"msg_stack_size is {msg_stack_size} and max_size is {max_lost_receive_msg_size}")
                return pass_time > judge_time and msg_stack_size < max_lost_receive_msg_size
        else:
            logger.info(f"need receive msg size [{receive_msg_size}] and actual receive size is [{msg_stack_size}]")
            return msg_stack_size < receive_msg_size

    def is_can_bus_lost(self, continue_time: int = 5) -> bool:
        """
        can?????????????????????????????????????????????????????????can????????????can??????????????????

        :param continue_time: ???????????????10s?????????????????????CAN????????????CAN????????????
        """
        # ???????????????
        self.clear_stack_data()
        time.sleep(continue_time)
        return len(self._can.get_stack()) == 0

    @staticmethod
    def is_msg_value_changed(stack: List[Message], msg_id: int) -> bool:
        """
        ????????????msg???????????????????????????????????????8byte?????????????????????

        :param stack: ???????????????CAN??????

        :param msg_id: ??????ID

        :return:
            True: ?????????

            False: ????????????
        """
        # ???????????????????????????
        data_list = list(filter(lambda x: x.msg_id == msg_id, stack))
        duplicate = set()
        for message in data_list:
            data = message.data
            duplicate.add(data)
        return len(duplicate) > 1

    @staticmethod
    def is_signal_value_changed(stack: List[Message], msg_id: int, signal_name: str) -> bool:
        """
        ????????????msg?????????signal???????????????

        :param stack: ???????????????CAN??????

        :param msg_id: ??????ID

        :param signal_name: ????????????

        :return:
            True: ?????????

            False: ????????????
        """
        # ???????????????????????????
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
        ??????????????????????????????
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
        ??????signal????????????????????????

        :param exact: ??????????????????

        :param msg_id: msg id

        :param signal_name:  sig name

        :param expect_value: expect value

        :param count: ????????????

        :param stack: ????????????
        """
        if msg_id is None:
            msg_id = self.__get_msg_id_from_signal_name(signal_name)
        if count:
            # ???????????????msg
            filter_messages = list(filter(lambda x: x.msg_id == msg_id, stack))
            logger.debug(f"filter messages length is {len(filter_messages)}")
            msg_count = 0
            for msg in filter_messages:
                logger.debug(f"msg data = {msg.data}")
                # ?????????msg??????data?????????????????????????????????
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
            # ????????????can??????????????????
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
        ??????????????????

        1???????????????????????????????????????

        2???????????????????????????

        3?????????????????????????????????

        :param default_message: ???????????????????????? {0x152: {"aaa": 0x1, "bbb": 0xc}, 0x119: {"ccc": 0x1, "ddd": 0x2}}

        :param filter_sender: ?????????????????????HU?????????????????????????????????

        :param cycle_time: ????????????

        :param interval: ????????????????????????????????????????????????0.1???

        :param filter_nm: ??????????????????????????????

        :param filter_diag: ????????????????????????
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
        ????????????filter_sender?????????????????????????????????????????????????????????????????????????????????

        :param filter_sender: ?????????????????????HU?????????????????????????????????
        """
        messages = self.__filter_messages(filter_sender)
        self.__send_messages(messages)

    def send_default_messages(self, filter_sender: Optional[FilterNode] = None):
        """
        ????????????node_name????????????????????????????????????????????????????????????????????????????????????????????????

        :param filter_sender: ????????????????????????
        """
        self.__restore_default_message()
        self.send_messages(filter_sender)
