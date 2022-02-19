# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        message
# @Author:      philosophy
# @Created:     2022/02/19 - 22:15
# --------------------------------------------------------
from typing import Union, List, Tuple, Dict

from ..logger import logger
from .dbc_parser import DbcParser
from ..utils import get_json_obj

Number = Union[int, float]
Values = Dict[str, str]
SignalType = Dict[str, Union[str, int, float, bool, Values]]
MessageType = Dict[str, Union[str, int, float, bool, List[SignalType]]]
Messages = List[MessageType]

"""
工具类，单独给CAN Service中的Parser使用，基本上不对外使用

该类的作用是根据start_bit和bit_length等值计算出来8byte的值或者反向计算。

如需要可以将该类变成私有类
"""

# 位长度
_bit_length = 8


def __completion_byte(byte_value: str, size: int = 8) -> str:
    """
    如果不足size位，补齐size位
    :return:
    """
    # 补齐8位
    while len(byte_value) != size:
        byte_value = "0" + byte_value
    return byte_value


def __get_position(start_bit: int, byte_length: int = 8) -> Tuple[int, int]:
    """
    获取start_bit在整个8Byte中占据的位置以及在1 Byte中的位置

    :param start_bit: 起始点

    :return: 8 Byte中占据的位置，1 Byte中占据的位置
    """
    # 根据start_bit以及bin_value_length计算占据的byte有几个
    # 计算start_bit是在第几个byte中，以及在byte中占据第几个bit
    # 获取开始点在整个8byte数据的位置
    logger.trace(f"start_bit = [{start_bit}] && byte_length = [{byte_length}]")
    byte_index = -1
    for i in range(byte_length):
        if _bit_length * i <= start_bit <= _bit_length * i + 7:
            byte_index = i
            break
    # 获取在单独这个byte中所占据的位置
    bit_index = 7 - (start_bit - (start_bit // 8 * 8))
    logger.trace(f"byte_index = [{byte_index}] && bit_index = [{bit_index}]")
    return byte_index, bit_index


def __split_bytes(value: str, length: int, bit_index: int, byte_type: bool) -> List[str]:
    """
    根据bit_index和length来算value拆分成几个byte
    :param value:  要设置的值
    :param length: 长度
    :param bit_index: start_bit在一个byte中的位置
    :return: byte集合
    """
    logger.trace(f"length is {length}, bit_index = {bit_index}")
    values = []
    if byte_type:
        if length > bit_index + 1:
            values.append(value[-bit_index - 1:])
            # 把剩下的拿出来
            value = value[:-bit_index - 1]
            logger.trace(f"rest value is [{value}]")
            while len(value) > _bit_length:
                # 当剩余数据长度大于8表示还有一个byte， 先把数据加入列表中
                values.append(value[-_bit_length:])
                # 然后截取剩余的部分
                value = value[:-_bit_length]
            # 最后把剩余的部分加到列表中
            values.append(value)
        else:
            # 只有一个byte
            values.append(value)
    else:
        if length > (_bit_length - bit_index):
            values.append(value[:_bit_length - bit_index])
            # 把剩下的拿出来
            value = value[_bit_length - bit_index:]
            logger.trace(f"rest value is [{value}]")
            while len(value) > _bit_length:
                # 当剩余数据长度大于8表示还有一个byte， 先把数据加入列表中
                values.append(value[:_bit_length])
                # 然后截取剩余的部分
                value = value[_bit_length:]
            # 最后把剩余的部分加到列表中
            values.append(value)
        else:
            # 只有一个byte
            values.append(value)
    return values


def check_value(value: Number, min_: Number, max_: Number) -> bool:
    """
    校验value是否处于min和max之间[min, max]

    :param value: 要校验的值

    :param min_: 最小值

    :param max_: 最大值

    :return:
        True: 正确
        False: 错误
    """
    return min_ <= value <= max_


def set_data(data: List[int], start_bit: int, byte_type: bool, value: int, bit_length: int, byte_length: int = 8):
    """
    用于设置每个Signal后，计算出8Byte的值

    :param bit_length: signal 长度

    :param value:  signal总线值

    :param byte_type:  True表示Intel， False表示Motorola MSB模式, DBC解析出来只支持MSB模式, 不支持LSB模式，

        对于LSB来说，在变成DBC的时候就处理了start bit

    :param start_bit: 起始位

    :param data: 总线8Byte数据

    :param byte_length: 字段长度，默认值为8，CAN FD可调整
    """
    logger.trace(f"data = {list(map(lambda x: hex(x), data))}), start_bit = [{start_bit}], "
                 f"byte_type = [{byte_type}], value = [{value}], bit_length = [{bit_length}]")
    byte_index, bit_index = __get_position(start_bit, byte_length)
    # True表示Intel， False表示Motorola MSB模式, DBC解析出来只支持MSB模式, 不支持LSB模式，
    # 对于LSB来说，在变成DBC的时候就处理了start bit
    # 根据位数来算， 其中把value转换成了二进制的字符串
    bin_value = __completion_byte(bin(value)[2:], bit_length)
    logger.trace(f"bin_value = {bin_value}")
    # 计算占据几个byte
    holder_bytes = __split_bytes(bin_value, bit_length, bit_index, byte_type)
    logger.trace(f"holder_bytes = {holder_bytes}")
    for index, byte in enumerate(holder_bytes):
        actual_index = byte_index + index
        logger.trace(f"actual index = {actual_index}")
        byte_value = __completion_byte(bin(data[actual_index])[2:])
        logger.trace(f"the [{byte_index}] value is [{byte_value}]")
        length = len(byte)
        logger.trace(f"byte  = {byte}")
        # 填充第一位
        if index == 0:
            if byte_type:
                logger.trace(f"intel mode")
                byte_value = byte_value[:bit_index + 1 - length] + byte + byte_value[bit_index + 1:]
            else:
                logger.trace("motorola mode")
                byte_value = byte_value[:bit_index] + byte + byte_value[bit_index + length:]
            logger.trace(f"first byte value = {byte_value}")
        # 填充最后一位
        elif index == len(holder_bytes) - 1:
            if byte_type:
                logger.trace(f"intel mode")
                byte_value = byte_value[:_bit_length - length] + byte
            else:
                logger.trace("motorola mode")
                byte_value = byte + byte_value[length:]
            logger.trace(f"last byte value = {byte_value}")
        # 填充中间的数据
        else:
            byte_value = byte
        logger.trace(f"after handle byte_value = {byte_value}")
        logger.trace(f"set {actual_index} data {bin(data[actual_index])[2:]} to {byte_value}")
        # 把计算后的值设置会data中去, 此处注意字符串要转成2进制
        data[actual_index] = int(byte_value, 2)
    logger.trace(f"parser data is = {list(map(lambda x: hex(x), data))}")


def get_data(data: List[int], start_bit: int, byte_type: bool, bit_length: int, byte_length: int = 8) -> int:
    """
    根据data计算出来每个signal的值

    :param bit_length: signal 长度

    :param byte_type:  True表示Intel， False表示Motorola MSB模式, DBC解析出来只支持MSB模式, 不支持LSB模式，

        对于LSB来说，在变成DBC的时候就处理了start bit

    :param start_bit: 起始位

    :param data: 8 byte数据

    :param byte_length: 字段长度，默认值为8，CAN FD可调整

    :return 查询到的值
    """
    logger.trace(f"data = {list(map(lambda x: hex(x), data))}), start_bit = [{start_bit}], "
                 f"byte_type = [{byte_type}], bit_length = [{bit_length}]")
    byte_index, bit_index = __get_position(start_bit, byte_length)
    byte_value = __completion_byte(bin(data[byte_index])[2:])
    logger.trace(f"the [{byte_index}] value is [{byte_value}]")
    if byte_type:
        logger.trace(f"intel mode")
        if bit_length > bit_index + 1:
            signal_value = byte_value[:bit_index + 1]
            logger.trace(f"intel first signal_value = {signal_value}")
            rest_length = bit_length - bit_index - 1
            logger.trace(f"intel rest length = {rest_length}")
            while rest_length > _bit_length:
                byte_index += 1
                byte_value = __completion_byte(bin(data[byte_index])[2:])
                logger.trace(f"the [{byte_index}] value is [{byte_value}]")
                signal_value = byte_value[:_bit_length] + signal_value
                logger.trace(f"intel middle signal_value = {signal_value}")
                rest_length = rest_length - _bit_length
            # 最后一个value
            byte_index += 1
            byte_value = __completion_byte(bin(data[byte_index])[2:])
            logger.trace(f"the [{byte_index}] value is [{byte_value}]")
            logger.trace(f"rest_length = {rest_length}")
            signal_value = byte_value[-rest_length:] + signal_value
            logger.trace(f"intel last signal_value = {signal_value}")
        else:
            signal_value = byte_value[bit_index + 1 - bit_length:bit_index + 1]
            logger.trace(f"only one byte value = {signal_value}")
    else:
        logger.trace(f"motorola mode")
        if bit_length > (_bit_length - bit_index):
            signal_value = byte_value[bit_index:]
            logger.trace(f"motorola first signal_value = {signal_value}")
            rest_length = bit_length - (_bit_length - bit_index)
            logger.trace(f"rest length = {rest_length}")
            while rest_length > _bit_length:
                byte_index += 1
                byte_value = __completion_byte(bin(data[byte_index])[2:])
                logger.trace(f"the [{byte_index}] value is [{byte_value}]")
                signal_value = signal_value + byte_value[:_bit_length]
                logger.trace(f"motorola middle signal_value = {signal_value}")
                rest_length = rest_length - _bit_length
            # 最后一个value
            byte_index += 1
            byte_value = __completion_byte(bin(data[byte_index])[2:])
            logger.trace(f"the [{byte_index}] value is [{byte_value}]")
            logger.trace(f"rest_length = {rest_length}")
            signal_value = signal_value + byte_value[:rest_length]
            logger.trace(f"motorola last signal_value = {signal_value}")
        else:
            signal_value = byte_value[bit_index:bit_index + bit_length]
    # 字符串转换成数字
    return int(signal_value, 2)


def get_message(messages: Union[str, Messages], encoding: str = "utf-8") -> Tuple[Dict, Dict]:
    """
    从Json或者python文件中获取id和name的message字典

    :param messages: json文件所在位置或者dbc转换出的python文件中的messages

    :param encoding: 编码格式，默认utf-8

    :return: （id_messages, name_messages）

        id_message是以id开头的字典类型，如{0x150: Message1, 0x151: Message2}, 其中Message1参考Message对象；

        name_message是以name开头的字典类型，如{"name1": Message1, "name2": Message2}, 其中Message1参考Message对象;

    """
    id_messages = dict()
    name_messages = dict()
    if isinstance(messages, str):
        message_name = messages
        if message_name.endswith(".json"):
            messages = get_json_obj(message_name, encoding=encoding)
        elif message_name.endswith(".dbc"):
            dbc_parser = DbcParser()
            messages = dbc_parser.parse(message_name, encoding="gbk")
        else:
            raise RuntimeError("messages only support json or dbc file")
    for msg in messages:
        message = Message()
        message.set_value(msg)
        id_messages[message.msg_id] = message
        name_messages[message.msg_name] = message
    logger.trace(f"total read message is {len(id_messages)}")
    return id_messages, name_messages


class Message(object):
    """
    CAN总线定义的Message，集合了CAN box发送的相关内容， 如msg_send_type/external_flag等

    CAN 矩阵表/DBC定义的相关数据，如signals等

    在设计signals的时候，由于signal的名字是唯一标识符，所以设计成了字典类型方便查找
    """

    def __init__(self):
        # 信号ID
        self.msg_id = None
        # 信号发送的周期
        self.cycle_time = 0
        # 信号数据长度
        self.data_length = None
        # 信号数据
        self.data = []
        # 信号停止标志
        self.stop_flag = False
        # 信号的名字
        self.msg_name = None
        # 信号发送者
        self.sender = None
        # signal
        self.signals = dict()
        # 时间印记
        self.time_stamp = None
        # 发送帧的帧长度
        self.frame_length = 1
        # 信号发送类型
        self.send_type = 0
        # message在CAN网络上发送类型（支持CYCLE/EVENT/CE)
        self.msg_send_type = None
        # 报文快速发送的次数
        self.cycle_time_fast_times = 0
        # 报文发送的快速周期
        self.cycle_time_fast = 0
        # 报文延时时间
        self.delay_time = 0
        # 是否是网络管理帧
        self.nm_message = False
        # diag请求
        self.diag_request = False
        # diag反馈
        self.diag_response = False
        # diag state
        self.diag_state = False
        # 是否标准can
        self.is_standard_can = None
        #################################################################################
        # USB MESSAGE独特的部分
        self.usb_can_send_type = 1
        # USB CAN特有的属性
        self.time_flag = 1
        # USB CAN特有的属性
        self.remote_flag = 0
        # USB CAN特有的属性
        self.external_flag = 0
        # 信号保留字
        self.reserved = None

    def __str__(self):
        return f"{hex(self.msg_id)} = {self.data}"

    def __check_msg_id(self):
        """
        检查msg id是否在0-07ff之间
        """
        if not check_value(self.msg_id, 0, 0x7FF):
            raise ValueError(f"msg id [{self.msg_id}] is incorrect, only support [0 - 0x7ff]")

    def __check_msg_data(self):
        """
        检查msg数据，8byte是否每个数据都在0-0xff之间
        """
        for value in self.data:
            if not check_value(value, 0, 0xff):
                raise ValueError(f"data[{self.data}] is incorrect, each value only support [0 - 0xff]")

    def __check_signals(self):
        """
        检查signals对象
        todo 需要根据signals对象的设置来检查
        """
        pass

    def check_message(self, need_check_data: bool = False):
        """
        检查message， 包含:

        1、检查msg id是否正确

        2、检查signal是否正确或者检查data是否正确

        :param need_check_data: 是否需要检查8byte的数据，默认不检查
        """
        self.__check_msg_id()
        if need_check_data:
            self.__check_msg_data()
        else:
            self.__check_signals()

    def update(self, type_: bool):
        """
        更新8byte数据。

        :param type_: 更新类型

            True: 发送数据

            False:  收到数据
        """
        # 发送数据
        if type_:
            logger.trace("send message")
            for name, signal in self.signals.items():
                logger.trace(f"signal name = {signal.signal_name} and signal value = {signal.value}")
                # 根据原来的数据message_data，替换某一部分的内容
                set_data(self.data, signal.start_bit, signal.byte_type, signal.value, signal.bit_length,
                         self.data_length)
            logger.trace(f"msg id {hex(self.msg_id)} and data is {list(map(lambda x: hex(x), self.data))}")
        # 收到数据
        else:
            logger.trace("receive message")
            for name, signal in self.signals.items():
                logger.trace(f"signal name = {signal.signal_name} and signal value = {signal.value}")
                value = get_data(self.data, signal.start_bit, signal.byte_type, signal.bit_length, self.data_length)
                logger.trace(f"value is {value}")
                signal.value = value

    def set_value(self, message: MessageType):
        """
        设置message对象

        TAG: 如果要增加或者变更内容，修改这里

        :param message: message字典
        """
        self.msg_id = message["id"]
        self.msg_name = message["name"]
        self.data_length = message["length"]
        # 根据data的长度来设置data的值
        for i in range(self.data_length):
            self.data.append(0)
        self.sender = message["sender"]
        #  特殊处理，如果不是Cycle/Event就是CE
        send_type = message["msg_send_type"]
        if send_type.upper() == "CYCLE":
            self.msg_send_type = "Cycle"
        elif send_type.upper() == "EVENT":
            self.msg_send_type = "Event"
        else:
            self.msg_send_type = "Cycle and Event"
        if "nm_message" in message:
            self.nm_message = message["nm_message"]
        else:
            self.nm_message = False
        self.diag_request = message["diag_request"]
        self.diag_response = message["diag_response"]
        self.diag_state = message["diag_state"]
        try:
            self.is_standard_can = message["is_standard_can"]
        except KeyError:
            self.is_standard_can = True
        try:
            self.cycle_time = message["msg_cycle_time"]
            # 必须加上msg_cycle_time大于0才可以判断当前信号为周期信号
            if self.cycle_time > 0:
                self.msg_send_type = "Cycle"
        except KeyError:
            self.cycle_time = 0
        try:
            self.delay_time = message["msg_delay_time"]
        except KeyError:
            self.delay_time = 0
        try:
            self.cycle_time_fast = message["msg_cycle_time_fast"]
        except KeyError:
            self.cycle_time_fast = 0
        try:
            self.cycle_time_fast_times = message["gen_msg_nr_of_repetition"]
        except KeyError:
            self.cycle_time_fast_times = 0

        for sig in message["signals"]:
            signal = Signal()
            signal.set_value(sig)
            self.signals[signal.signal_name] = signal


class Signal(object):
    def __init__(self):
        # 信号的名字
        self.signal_name = None
        # 信号的位长度
        self.bit_length = None
        # 模式  intel还是motorola
        self.byte_type = None
        # 信号的开始位
        self.start_bit = None
        # 计算因子
        self.factor = None
        # 偏移量
        self.offset = None
        # 最大物理值
        self.maximum = None
        # 最小物理值
        self.minimum = None
        # 接收者
        self.receiver = None
        # 有无符号
        self.is_sign = None
        # 单位
        self.unit = None
        # 备注
        self.comment = None
        # 对应值
        self.values = 0
        # 设置的值
        self.__value = 0
        # 物理值
        self.__physical_value = None

    def set_value(self, signal: SignalType):
        """
        设置signal的值

        TAG: 如果要增加或者变更内容，修改这里

        :param signal: signal字典
        """
        self.signal_name = signal["name"]
        self.bit_length = signal['signal_size']
        self.start_bit = signal["start_bit"]
        self.is_sign = signal["is_sign"]
        self.byte_type = signal["byte_type"]
        self.factor = signal["factor"]
        self.offset = signal["offset"]
        self.minimum = signal["minimum"]
        self.maximum = signal["maximum"]
        self.unit = signal["unit"]
        self.receiver = signal["receiver"]
        if "start_value" in signal:
            self.value = signal["start_value"]
        else:
            self.value = 0
        try:
            self.values = signal["values"]
        except KeyError:
            self.values = None
        try:
            self.comment = signal["comment"]
        except KeyError:
            self.comment = ""

    def check_value(self, need_check: bool = False):
        """
        检查信号的值

        :param need_check： 是否检查值是否处于物理值最大最小值之间
        """
        if need_check:
            if self.is_sign:
                if not float(self.minimum) <= self.value <= float(self.maximum):
                    raise ValueError(f"value[{self.value}] must in [{self.minimum} , {self.maximum}]")
            else:
                if not int(self.minimum) <= self.value <= int(self.maximum):
                    raise ValueError(f"value[{self.value}] must in [{self.minimum} , {self.maximum}]")
        # 检查当前设置的最大值是否超过bit length所允许的最大值
        max_value = 2 ** self.bit_length - 1
        if not check_value(self.value, 0, max_value):
            raise ValueError(f"value[{self.value}] must in [0, {max_value}]")

    def check_start_bit_value(self):
        """
        检查start bit是否设置正确
        """
        if not check_value(self.start_bit, 0, 0x3f):
            raise ValueError(f"start bit[{self.start_bit}] must in [0, 0x3f]")

    def check_bit_length_value(self):
        """
        检查bit length是否设置正确
        """
        if not check_value(self.bit_length, 0, 0x3f):
            raise ValueError(f"start bit[{self.bit_length}] must in [0, 0x3f]")

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        """
        收到的消息，
        """
        self.__value = value
        self.__physical_value = int((float(value) * float(self.factor)) + float(self.offset))
        logger.debug(f"signal[{self.signal_name}]value is {self.__value} and physical value is {self.__physical_value}")

    @property
    def physical_value(self):
        return self.__physical_value

    @physical_value.setter
    def physical_value(self, physical_value: Number):
        self.__physical_value = physical_value
        self.__value = int((float(physical_value) - float(self.offset)) / float(self.factor))
        if self.__value < 0 or self.__value > (2 ** self.bit_length - 1):
            raise RuntimeError("it need input physical value not bus value")
        logger.debug(f"physical value is {self.__physical_value} and value is {self.__value}")
