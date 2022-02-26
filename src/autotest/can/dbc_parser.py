# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        dbc_parser
# @Author:      philosophy
# @Created:     2022/02/19 - 22:06
# --------------------------------------------------------
import copy
import json
import re
from typing import List, Dict, Any

from automotive.logger.logger import logger


class DbcParser(object):
    # 定义常量
    BLANK = " "
    GBK = "gbk"
    UTF8 = "utf-8"
    TRIM_BLANK = "\\s+"
    Y_AXIS = r"|"
    QUOTATION = "\""
    SEMICOLON = ";"
    PLUS = "+"
    COMMA = ","
    POINT = "."
    COLON = ":"
    COLON_CHINESE = "："
    AT = "@"
    NULL = ""
    YES = "YES"
    YES_CHINESE = "是"
    ONE = "1"
    INT = "INT"
    ENUM = "ENUM"
    STRING = "STRING"
    HEX = "HEX"
    EV = "EV_ "
    BO = "BO_ "
    SG = "SG_ "
    CM_ONLY = "CM_ "
    CM_ONLY_QUOTATION = "CM_ \""
    CM = "CM_ SG_ "
    VAL = "VAL_ "
    BA = "BA_ "
    BU = "BU_ "
    BA_DEF = "BA_DEF_ "
    BA_DEF_REL = "BA_DEF_REL_ "
    BA_DEF_DEF = "BA_DEF_DEF_ "
    BA_DEF_DEF_REL = "BA_DEF_DEF_REL_ "
    VAL_TABLE = "VAL_TABLE_ "
    GEN_MSG_NR_OF_REPETITION = "GenMsgNrOfRepetition"
    GEN_MSG_CYCLE_TIME_FAST = "GenMsgCycleTimeFast"
    GEN_MSG_DELAY_TIME = "GenMsgDelayTime"
    GEN_MSG_SEND_TYPE = "GenMsgSendType"
    GEN_MSG_CYCLE_TIME = "GenMsgCycleTime"
    V_FRAME_FORMAT = "VFrameFormat"
    NM_MESSAGE = "NmMessage"
    NM_ASR_MESSAGE = "NmAsrMessage"
    DIAG_STATE = "DiagState"
    DIAG_REQUEST = "DiagRequest"
    DIAG_RESPONSE = "DiagResponse"
    STANDARD_CAN = "StandardCAN"
    STANDARD_CAN_FD = "StandardCAN_FD"
    GEN_SIG_START_VALUE = "GenSigStartValue"
    MODE_TRANSMISSION = "ModeTransmission"
    PERIOD = "P茅riode"
    DIAG = "Diag"
    NM = "NM"
    NORMAL = "Normal"
    REQUEST = "request"
    RECEIVE = "r"
    SEND = "s"
    MOTOROLA = "motorola"
    LSB = "lsb"
    MSB = "msg"
    UNSIGNED = "unsigned"
    RIGHT_BRACKETS = ")"
    RIGHT_CENTER_BRACKETS = "]"

    def parse(self, dbc_file: str, encoding: str = "gbk") -> List[Dict[str, Any]]:
        """
        解析DBC文件为列表类型
        :param encoding: 编码格式
        :param dbc_file: DBC文件
        :return: messages
        """
        contents = self.__read_content(dbc_file, encoding)
        logger.trace(f"contents = {contents}")
        messages = self.__parse_message(contents)
        return self.__filter_messages(messages)

    def parse_to_file(self, dbc_file: str, json_file: str):
        """
        解析DBC文件并以json方式写入到文件中
        :param dbc_file:  DBC文件
        :param json_file: 输出的json文件
        """
        messages = self.parse(dbc_file)
        json_str = json.dumps(messages, ensure_ascii=False, indent=4)
        with open(json_file, "w", encoding="utf-8") as f:
            f.write(json_str)

    def __filter_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去除掉大于0x7ff的数据
        :param messages:
        :return:
        """
        new_messages = copy.deepcopy(messages)
        msg_ids = []
        for i, message in enumerate(new_messages):
            if message["id"] > 0x7ff:
                msg_ids.append(i)
        for msg_id in msg_ids:
            new_messages.pop(msg_id)
        self.__set_message_default_value(new_messages)
        return new_messages

    @staticmethod
    def __judge_content(content: str, *args):
        """
        判断是否包含某个文字
        :param content:  文本
        :param args: 参数
        :return:
        """
        for arg in args:
            if arg in content:
                return True
        return False

    def __get_content(self, content: str, replace_type: str):
        """
        获取处理后的字符
        :param content: dbc文件中读取到的内容
        :param replace_type:  取代的文字
        :return: 处理后的字符串
        """
        return content.replace(replace_type, self.NULL) \
            .replace(self.TRIM_BLANK, self.BLANK) \
            .replace(self.SEMICOLON, self.NULL) \
            .strip()

    def __get_val_content(self, content: str) -> str:
        """
        处理VAL行数据
        :param content:  dbc文件中读取到的内容
        :return: 处理后的字符串
        """
        return content.replace(self.VAL, self.NULL) \
            .replace(self.TRIM_BLANK, self.BLANK) \
            .replace(f"{self.BLANK}{self.QUOTATION}{self.BLANK}", f"{self.BLANK}{self.QUOTATION}") \
            .strip()

    @staticmethod
    def __get_message_by_id(messages: List[Dict[str, List[Any]]],
                            message_id: int) -> Dict[str, List[Any]]:
        """
        根据id获取message字典
        """
        for message in messages:
            if message["id"] == message_id:
                return message
        raise RuntimeError(f"no message id[{message_id}] found in messages")

    @staticmethod
    def __get_signal_by_name(signals: List[Dict[str, Any]], name: str) -> Dict[str, Any]:
        """
        根据名字获取signal
        """
        for signal in signals:
            if signal["name"] == name:
                return signal
        raise RuntimeError(f"no signal name[{name}] found in signal")

    @staticmethod
    def __read_from_file(dbc_file: str, encoding: str) -> List[str]:
        try:
            with open(dbc_file, "r", encoding=encoding) as f:
                contents = f.readlines()
                return contents
        except UnicodeDecodeError:
            try:
                with open(dbc_file, "r", encoding="utf-8") as f:
                    contents = f.readlines()
                    return contents
            except UnicodeDecodeError:
                with open(dbc_file, "r", encoding="GB18030") as f:
                    contents = f.readlines()
                    return contents

    def __read_content(self, dbc_file: str, encoding: str) -> List[str]:
        """
        从DBC文件中读取数据并且处理多行的情况
        :param dbc_file: dbc文件
        :return: 处理后的数据串列表
        """
        # 处理后的数据
        after_handle_contents = []
        contents = self.__read_from_file(dbc_file, encoding)
        final_content = ""
        need_add = True
        for index, content in enumerate(contents):
            # 去掉空行
            content = content.strip()
            logger.trace(f"index = {index} and content is {content}")
            if self.__judge_content(content, self.BO, self.SG, self.CM, self.BA_DEF, self.BA_DEF_DEF,
                                    self.BA_DEF_DEF_REL, self.BA_DEF_REL, self.BA, self.VAL):
                need_add = True
                if len(final_content) != 0:
                    after_handle_contents.append(final_content)
                    final_content = ""
                final_content += content
            elif self.__judge_content(content, self.CM_ONLY_QUOTATION):
                need_add = False
            else:
                if need_add:
                    final_content += content + self.BLANK
        return after_handle_contents

    @staticmethod
    def __set_message_default_value(messages: List[Dict[str, Any]]):
        """
        设置message默认的值
        """
        for message in messages:
            if "diag_request" not in message:
                message["diag_request"] = False
            if "diag_response" not in message:
                message["diag_response"] = False
            if "diag_state" not in message:
                message["diag_state"] = False
            if "gen_msg_nr_of_repetition" not in message:
                message["gen_msg_nr_of_repetition"] = 0
            if "is_can_fd" not in message:
                message["is_can_fd"] = False
            if "is_standard_can" not in message:
                message["is_standard_can"] = False
            if "msg_cycle_time_fast" not in message:
                message["msg_cycle_time_fast"] = 0
            if "msg_delay_time" not in message:
                message["msg_delay_time"] = 0
            if "nm_message" not in message:
                message["nm_message"] = False

    def __parse_message(self, contents: List[str]) -> List[Dict[str, Any]]:
        cm_flag = True
        attr_dict = dict()
        messages = []
        message = dict()
        signals = []
        # 上一行是BO，这一行不是BO导致没有把数据传上去
        for content in contents:
            # 处理BO行，及Message
            if content.startswith(self.BO):
                if len(message) != 0:
                    if not content.startswith(self.SG):
                        message["signals"] = signals
                        messages.append(message)
                        message = dict()
                        signals = []
                    if content.startswith(self.BO):
                        self.__set_message(message, content)
                else:
                    self.__set_message(message, content)
            # 处理SG行，主要是signal
            if content.startswith(self.SG):
                signal = self.__get_signal(content)
                logger.trace(f"signal = {signal}")
                signals.append(signal)
            # 处理CM行
            if content.startswith(self.CM):
                # 处理剩下的BO
                if cm_flag:
                    message["signals"] = signals
                    messages.append(message)
                    signals = []
                    # message.clear()
                    cm_flag = False
                self.__set_comments(messages, content)
            # 处理BA_DEF行 （BA的定义）
            if content.startswith(self.BA_DEF):
                self.__set_message_attribute(attr_dict, content)
            # 处理BA_DEF_DEF行 （BA的默认值）
            if content.startswith(self.BA_DEF_DEF):
                self.__set_default_value(messages, content)
            # 处理BA行
            if content.startswith(self.BA):
                self.__set_ba_values(messages, attr_dict, content)
            # 处理VAL行
            if content.startswith(self.VAL):
                self.__set_val_values(messages, content)
        logger.trace(f"messages = {messages}")
        return messages

    def __set_val_values(self, messages: List[Dict[str, Any]], content: str):
        """
        /*
         *  处理VAL模块，返回键值对
         *  VAL_ 1069 BCU_BalnFlg105_RM 1 "Balance Closed" 0 "Balance Open" ;
         */
        """
        # 1069 BCU_BalnFlg105_RM 1 "Balance Closed" 0 "Balance Open" ;
        val = self.__get_val_content(content)
        val = val.replace(self.SEMICOLON, self.BLANK).strip()
        blank_index = val.index(self.BLANK)
        message_id = int(val[:blank_index].strip())
        # BCU_BalnFlg105_RM 1 "Balance Closed" 0 "Balance Open"
        other = val[blank_index + 1:]
        logger.trace(f"parse blank_index other = [{other}]")
        blank_index = other.index(self.BLANK)
        signal_name = other[:blank_index]
        # 1 "Balance Closed" 0 "Balance Open"
        other = other[blank_index + 1:]
        logger.trace(f"parse blank_index other = [{other}]")
        values = dict()
        while len(other) > 0:
            quotation_index = other.index(self.QUOTATION)
            key = other[:quotation_index].strip()
            other = other[quotation_index + 1:].strip()
            quotation_index = other.index(self.QUOTATION)
            value = other[:quotation_index].strip()
            other = other[quotation_index + 1:].strip()
            values[key] = re.sub(self.TRIM_BLANK, self.BLANK, value)
        message = self.__get_message_by_id(messages, message_id)
        signal = self.__get_signal_by_name(message["signals"], signal_name)
        signal["values"] = values

    def __set_ba_values(self, messages: List[Dict[str, Any]], attr_dict: Dict[str, Any], content: str):
        """
        /*
         * 处理BA_ "GenMsgDelayTime" BO_ 1069 0;
         *    BA_ "GenSigStartValue" SG_ 994 ESC_ReqTargetExternal 32256;
         */
        """
        logger.trace(f"attr_dict = {attr_dict}")
        ba = self.__get_content(content, self.BA)
        logger.trace(f"ba = {ba}")
        ba = ba.replace(self.SEMICOLON, self.NULL) \
            .replace(self.QUOTATION, self.NULL) \
            .replace(f"{self.BLANK}{self.BLANK}", self.BLANK) \
            .strip()
        if self.BO in ba:
            split = ba.split(self.BLANK)
            logger.trace(f"split is {split}")
            name = split[0].strip()
            message_id = int(split[2].strip())
            value = split[3].strip()
            message = self.__get_message_by_id(messages, message_id)
            logger.trace(f"msg id = [{message_id}] && message is {message}")
            self.__handle_bo(message, name, value, attr_dict)
        elif self.SG in ba:
            split = ba.split(self.BLANK)
            name = split[0].strip()
            message_id = int(split[2].strip())
            signal_name = split[3].strip()
            value = split[4].strip()
            message = self.__get_message_by_id(messages, message_id)
            logger.trace(f"msg id = [{message_id}] && message is {message}")
            self.__handle_sg(message, name, signal_name, value)
        else:
            logger.trace(f"not standard ba")

    def __handle_bo(self, message: Dict[str, Any], name: str, value: str, attr_dict: Dict[str, str]):
        logger.trace(f"attr_dict = {attr_dict}")
        logger.trace(f"type = [{name}] and value = [{value}]")
        if name == self.GEN_MSG_CYCLE_TIME_FAST:
            message["msg_cycle_time_fast"] = int(value)
        elif name == self.GEN_MSG_NR_OF_REPETITION:
            message["gen_msg_nr_of_repetition"] = int(value)
        elif name == self.GEN_MSG_DELAY_TIME:
            message["msg_delay_time"] = int(value)
        elif name == self.GEN_MSG_SEND_TYPE:
            send_type = attr_dict[name][int(value)]
            message["msg_send_type"] = send_type
        elif name == self.GEN_MSG_CYCLE_TIME:
            message["msg_cycle_time"] = int(value)
        elif name == self.NM_MESSAGE or name == self.NM_ASR_MESSAGE:
            nm_value = attr_dict[name][int(value)]
            message["nm_message"] = True if self.YES.upper() == nm_value.upper() else False
        elif name == self.DIAG_STATE:
            diag_value = attr_dict[name][int(value)]
            message["diag_state"] = True if self.YES.upper() == diag_value.upper() else False
        elif name == self.DIAG_REQUEST:
            diag_value = attr_dict[name][int(value)]
            message["diag_request"] = True if self.YES.upper() == diag_value.upper() else False
        elif name == self.DIAG_RESPONSE:
            diag_value = attr_dict[name][int(value)]
            message["diag_response"] = True if self.YES.upper() == diag_value.upper() else False
        elif name == self.V_FRAME_FORMAT:
            message["is_standard_can"] = True if self.STANDARD_CAN.upper() == value.upper() else False
        # 针对PSA的DBC做的workaround
        elif name == self.MODE_TRANSMISSION:
            mode_value = attr_dict[name][int(value)]
            if mode_value == "P":
                message["msg_send_type"] = "Cycle"
            elif mode_value == "E":
                message["msg_send_type"] = "Event"
            elif mode_value == "P+E":
                message["msg_send_type"] = "CE"
        elif name == self.PERIOD:
            message["msg_cycle_time"] = int(value)
        else:
            logger.debug(f"type is {name}, so nothing to do")

    def __handle_sg(self, message: Dict[str, Any], name: str, signal_name: str, value: str):
        signal = self.__get_signal_by_name(message["signals"], signal_name)
        if name.upper() == self.GEN_SIG_START_VALUE.upper():
            logger.trace(f"value is {value}")
            if self.POINT in value:
                signal["start_value"] = float(value)
            else:
                signal["start_value"] = int(value)

    def __set_default_value(self, messages: List[Dict[str, Any]], content: str):
        """
        /*
         *  BA_DEF_DEF_  "GatewayedSignals" "No";
         */
        """
        ba_def_def = self.__get_content(content, self.BA_DEF_DEF)
        logger.trace(f"ba_def_def  = {ba_def_def}")
        split = ba_def_def.split(self.BLANK)
        if len(split) == 2:
            name = split[0].replace(self.QUOTATION, self.NULL)
            value = split[1].replace(self.QUOTATION, self.NULL)
            logger.trace(f"name = [{name}] and value = [{value}]")
            if name == self.GEN_MSG_CYCLE_TIME_FAST:
                for message in messages:
                    message["msg_cycle_time_fast"] = int(value)
            elif name.upper() == self.V_FRAME_FORMAT.upper():
                for message in messages:
                    message["is_standard_can"] = True if self.STANDARD_CAN == value else False
            elif name == self.GEN_MSG_NR_OF_REPETITION:
                for message in messages:
                    message["gen_msg_nr_of_repetition"] = int(value)
            elif name == self.GEN_MSG_CYCLE_TIME:
                for message in messages:
                    message["msg_cycle_time"] = int(value)
            elif name == self.GEN_MSG_DELAY_TIME:
                for message in messages:
                    message["msg_delay_time"] = int(value)
            elif name == self.GEN_MSG_SEND_TYPE:
                for message in messages:
                    message["msg_send_type"] = value
            elif name == self.NM_MESSAGE:
                for message in messages:
                    message["nm_message"] = True if self.YES == value else False
            elif name == self.DIAG_STATE:
                for message in messages:
                    message["diag_state"] = True if self.YES == value else False
            elif name == self.DIAG_REQUEST:
                for message in messages:
                    message["diag_request"] = True if self.YES == value else False
            elif name == self.DIAG_RESPONSE:
                for message in messages:
                    message["diag_response"] = True if self.YES == value else False
            elif name == self.STANDARD_CAN_FD:
                for message in messages:
                    message["is_standard_can"] = False if self.STANDARD_CAN == value else True
            elif name == self.GEN_SIG_START_VALUE:
                for message in messages:
                    signals = message["signals"]
                    if len(signals) != 0:
                        for signal in signals:
                            signal["start_value"] = int(value)
            else:
                logger.trace(f"ba default type is [{name}], so nothing to do")

    def __set_message_attribute(self, attr_dict: Dict[str, Any], content: str):
        """
        /*
         *  解析BA_DEF_ SG_  "GenSigInactiveValue" INT 0 10000;
         */
        """
        # BO_  "DiagResponse" ENUM  "No","Yes";
        ba_def = self.__get_content(content, self.BA_DEF)
        logger.trace(f"ba def  = {ba_def}")
        if not self.__judge_content(ba_def, self.BU, self.BO, self.EV, self.SG):
            logger.trace(f"no {self.BU}，{self.BO}，{self.EV}，{self.SG} found in content[{content}]")
            # "Manufactor" STRING ;
            logger.trace("暂时不处理这类数据")
        else:
            blank_index = ba_def.index(self.BLANK)
            node_type = ba_def[:blank_index]
            logger.trace(f"node_type is {node_type}")
            # "DiagResponse" ENUM  "No","Yes";
            other = ba_def[blank_index + 1:] \
                .strip() \
                .replace(self.QUOTATION, self.NULL) \
                .replace(self.SEMICOLON, self.NULL)
            logger.trace(f"parse blank_index other = [{other}]")
            # TpApplType STRING
            blank_index = other.index(self.BLANK)
            name = other[:blank_index].strip()
            # ENUM  "No","Yes";
            other = other[blank_index + 1:]
            logger.trace(f"parse blank_index other = [{other}]")
            if self.BLANK in other:
                blank_index = other.index(self.BLANK)
                attr_type = other[:blank_index].strip()
                logger.trace(f"attr_type = {attr_type}")
                # "No","Yes";
                other = other[blank_index + 1:].strip()
                if attr_type.upper() == self.INT.upper() \
                        or attr_type.upper() == self.HEX.upper():
                    logger.trace(f"attr_dict[{name}] = {other}")
                    attr_dict[name] = other
                elif attr_type.upper() == self.ENUM:
                    attr_dict[name] = other.split(self.COMMA)
                    logger.trace(f"ENUM attr_dict[{name}] = {other}")

    def __set_comments(self, messages: List[Dict[str, Any]], content: str):
        """
        /*
         *  处理CM模块的，返回键值对
         *  CM_ SG_ 643 HU_SeatVertAdjMotTarPosn "Seat Vertical Adjust Motor Target Position 座椅垂直调节电机目标位置";
         *  解析案例
         *  comment = 'CM_' (char_string |
         *  'BU_' node_name char_string |
         *  'BO_' message_id char_string |
         *  'SG_' message_id signal_name char_string |
         *  'EV_' env_var_name char_string)
         *  ';' ;
         */
        """
        logger.trace(f"cm content = {content}")
        if not self.__judge_content(content, self.BU, self.BO, self.EV, self.SG):
            raise ValueError(f"not {self.BU}, {self.BO}, {self.EV}, {self.SG} found in content[{content}]")
        cm = self.__get_content(content, self.CM_ONLY)
        logger.trace(f"cm = {cm}")
        if self.SG in cm:
            cm = cm.replace(self.SG, self.BLANK).strip()
            # SG_ 643 HU_SeatVertAdjMotTarPosn "Seat Vertical Adjust Motor Target Position 座椅垂直调节电机目标位置";
            blank_index = cm.index(self.BLANK)
            message_id = int(cm[:blank_index])
            # HU_SeatVertAdjMotTarPosn "Seat Vertical Adjust Motor Target Position 座椅垂直调节电机目标位置";
            other = cm[blank_index + 1:].strip()
            logger.trace(f"parse blank_index other = [{other}]")
            blank_index = other.index(self.BLANK)
            signal_name = other[:blank_index]
            other = other[blank_index + 1:].strip()
            logger.trace(f"parse blank_index other = [{other}]")
            # "Seat Vertical Adjust Motor Target Position 座椅垂直调节电机目标位置";
            comment = other.replace(self.QUOTATION, self.BLANK).replace(self.SEMICOLON, self.BLANK)
            message = self.__get_message_by_id(messages, message_id)
            signal = self.__get_signal_by_name(message["signals"], signal_name)
            signal["comment"] = re.sub(self.TRIM_BLANK, self.BLANK, comment).strip()

    def __set_message(self, message: Dict[str, Any], content: str):
        """
        /*
         * 处理BO模块的，返回键值对
         * BO_ 883 GW_373: 8 Vector__XXX
         * 解析案例
         * BO_ message_id message_name ':' message_size transmitter {signal} ;
         * 以及SG_ BCM_PMSErrorFlag : 13|2@0+ (1,0) [0|3] ""  HU
         */
        """
        bo = self.__get_content(content, self.BO)
        logger.trace(f"bo = {bo}")
        # 883 GW_373: 8 Vector__XXX
        blank_index = bo.index(self.BLANK)
        message_id = bo[:blank_index].strip()
        message["id"] = int(message_id)
        # GW_373: 8 Vector__XXX
        other = bo[blank_index + 1:]
        logger.trace(f"parse blank_index other = [{other}]")
        colon_index = other.index(self.COLON)
        name = other[:colon_index].strip()
        message["name"] = name
        # 8 Vector__XXX
        other = other[colon_index + 1:].strip()
        logger.trace(f"parse colon_index other = [{other}]")
        rest = other.split(self.BLANK)
        length = rest[0].strip()
        sender = rest[1].strip()
        message["length"] = int(length)
        message["sender"] = sender
        logger.trace(f"message = {message}")

    def __get_signal(self, content: str) -> Dict[str, Any]:
        """
        /*
         *  处理SG模块，返回键值对
         *  SG_ HVACF_NMSleepAck : 13|1@0+ (1,0) [0|1] ""  HVACR
         *  SG_ HU_LocTiY : 6|5@0+ (1,2019) [2019|2050] "year" TBox,CGW
         *  解析案例
         *  signal = 'SG_' signal_name multiplexer_indicator ':' start_bit '|'
         *  signal_size '@' byte_order value_type '(' factor ',' offset ')'
         *  '[' minimum '|' maximum ']' unit receiver {',' receiver} ;
         *  大端还是小端 1=intel(小端模式) ，0=Motorola（大端模式）
         *  由于在DBC只有一个bit，所以只能表达Intel和MOTOROLA两种方式, 推论应该是在DBC excel描述的时候需要做转换。
         *  True表示intel， False表示Motorola
         *  大端模式表示反向，小端模式表示顺向
         */
        """
        signal = dict()
        logger.trace(f"content = {content}")
        sg = self.__get_content(content, self.SG)
        logger.trace(f"sg = {sg}")
        #  分割第一个:
        colon_index = sg.index(self.COLON)
        logger.trace(f"colon_index position is {colon_index}")
        name = sg[:colon_index].strip()
        logger.trace(f"name = [{name}]")
        # 加参数到对象中
        signal["name"] = name
        # 6|5@0+ (1,2019) [2019|2050] "year" TBox,CGW
        other = sg[colon_index + 1:].strip()
        logger.trace(f"parse colon_index other = [{other}]")
        y_axis_index = other.index(self.Y_AXIS)
        start_bit = other[:y_axis_index].strip()
        signal["start_bit"] = int(start_bit)
        # 5@0+ (1,2019) [2019|2050] "year" TBox,CGW
        other = other[y_axis_index + 1:].strip()
        logger.trace(f"parse y_axis_index other = [{other}]")
        at_index = other.index(self.AT)
        bit_size = other[:at_index]
        signal["signal_size"] = int(bit_size)
        # 0+ (1,2019) [2019|2050] "year" TBox,CGW
        other = other[at_index + 1:].strip()
        logger.trace(f"parse at_index other = [{other}]")
        byte_order = other[0]
        value_type = other[1]
        signal["byte_type"] = True if byte_order == self.ONE else False
        signal["is_sign"] = True if value_type == self.PLUS else False
        # (1,2019) [2019|2050] "year" TBox,CGW
        other = other[2:].strip()
        logger.trace(f"parse other = [{other}]")
        right_brackets_index = other.index(self.RIGHT_BRACKETS)
        factor_offset = other[1:right_brackets_index].split(self.COMMA)
        factor = factor_offset[0].strip()
        offset = factor_offset[1].strip()
        signal["factor"] = float(factor)
        signal["offset"] = float(offset)
        # [2019|2050] "year" TBox,CGW
        other = other[right_brackets_index + 1:].strip()
        logger.trace(f"parse right_brackets_index other = [{other}]")
        right_center_brackets_index = other.index(self.RIGHT_CENTER_BRACKETS)
        max_min = other[1:right_center_brackets_index].split(self.Y_AXIS)
        minimum = max_min[0].strip()
        maximum = max_min[1].strip()
        signal["minimum"] = float(minimum)
        signal["maximum"] = float(maximum)
        # "year" TBox,CGW
        other = other[right_center_brackets_index + 1:].strip()[1:]
        logger.trace(f"parse right_center_brackets_index other = [{other}]")
        quotation_index = other.index(self.QUOTATION)
        unit = other[:quotation_index]
        signal["unit"] = unit
        other = other[quotation_index + 1:].strip()
        receivers = other.split(self.COMMA)
        signal["receiver"] = ",".join(receivers)
        return signal
