# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2020, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        konstanter.py
# @Author:      philosophy
# @Created:     2021/5/1 - 23:59
# --------------------------------------------------------
from time import sleep
from typing import Optional

from ..checker import check_connect, battery_tips
from ..logger import logger
from ..utils.serial_utils import serial_port


class Konstanter(object):
    """
        KONSTANTER SSP 240-20可编程电源：

        1.电源电压设置范围0-20.000， 电流设置范围0-20.000

        2.电源最大输出功率240W

        3.当以恒压输出模式时（CV），当电压达到20V时，电流最大只能设置到12A

        4.当以恒流输出模式时（CC），当电流达到20A时，电压最大只能设置到12V

        5.该系列的电源可通过Serial串口和IEEE488来进行控制，但本电源只支持serial方式

        6.本电源可以通过串口OUT端构成电源网络

        7.Uset，Iset：设置输出的电压电流值

        8.Ulim，Ilim：设置可设置的电压电流的上限值，上限值本身不能超过电源支持的最大值，即20V，20A

        9.OVP，OCP：过压保护和过流保护，设置后当外部短路时电源会自动切断输出，保证负载不损坏

        10.dLY：过流保护发生时进行一小段时间的延迟再断电

        11.Uout，Iout，Pout：实际的电压、电流和功率输出，一般小于【7】中的设置值

        12.AnIF：模拟接口输出组，电源后面串口接口下面的一排硬件端口，暂时可不关注

        13.SEQ：序列化输出，电源本身支持序列化输出电压，将不同的电压、电流和时间设置到11-255的寄存器中，然后便可以
                根据寄存器的顺序调用这个参数来输出对应的电压，该过程在设置好之后由电源自身执行，不需要外部干预，在
                执行过程中可以通过一些命令对序列化过程进行暂停、恢复、停止等操作

        14.tSet：在步骤【13】中的时间设置，主要出现在面板操作中，代码操作中直接调用store接口即可

        15.SSET：目前暂不清楚具体作用，主要与【12】所说的模拟接口输出相关

        16.tDEF：全局的时间定义，即当【14】中的时间未定义时使用该时间定义的值

        17.Strt：序列化开始的寄存器地址，序列化的执行涉及到几个关键的步骤：寄存器（主要使用11-255）、开始地址（如11）、
                停止地址（如31）、重复次数（如20），开始序列化执行后，电源会自动读取寄存器开始地址11中的电压、电流和
                时间参数，然后按照该读取的电压电流值输出，然后等待读取的时间后再读取下一个寄存器12中的值，如此循环
                直到达到停止地址对应的寄存器，以上过程代表完成了1次循环，重复执行以上步骤20后自动停止

        18.Stop：序列化停止的寄存器地址，同【17】

        19.rEP：序列化需要重复的次数，见【17】

        20.以下描述如何设置一次完整的序列化执行，主要是在代码实现中：

            (1).调用store函数，第一个参数是要设置的寄存器地址，第二个参数是要设置的电压值，第三个参数是要设置的电流值，
                第四个参数是电压保持的时间

            (2).多次调用store设置多个连续的寄存器中的值，如：11 12 13 14 15 16 17 18 20

            (3).设置完成后调用start_stop方法设置序列化执行的起始寄存器地址和停止寄存器地址，如11， 20

            (4).调用sequence_repetition函数设置序列化要重复执行的次数

            (5).最后调用sequence方法，传入参数'GO'表示开始序列化执行，后续电源自身便开始循环执行

            (6).如果过程中需要暂停或停止，可以调用sequence方法并传入其他参数操作

        21.电源共有0-255个寄存器，其中0-10为一些状态寄存器，如使能某功能的寄存器，清除某数据的寄存器等；11-255为可用于
            序列化设置参数的寄存器

        22.电压的响应时间最小为0.01s即10ms，小于该精度的部分将自动被丢弃

        23.电压精度为0.001，电流精度为0.001，可设置寄存器11-255，时间设置0.01-99.99，设置报错时请首先检查参数是否超范围

        24.所有的信息读取均使用get方法，只有11-255寄存器的读取使用get_store方法，其余全部为设置功能或参数的方法，所有的
            读取操作均返回字符串，目前暂无解析的需求

        25.以下按照是否常用列出所有的接口，排在最前面的为最常用的方法，越靠后可以不用关注,(1)-(12)为最常用的：

            (1). close:                             程序执行最后需要调用该接口关闭串口

            (2). output_enable:                     输出使能，设置好电流电压后使能输出才能输出电压，即面板上的OUTPUT按钮

            (3). set_voltage:                       设置输出电压，小于电压上限值

            (4). set_current:                       设置输出电流，小于电流上限值

            (5). set_voltage_limit:                 设置电压上限值，小于等于20V

            (6). set_current_limit:                 设置电流上限值，小于等于20A

            (7). store:                             序列化执行前需要调用该方法设置寄存器参数

            (8). sequence:                          序列化执行开始、结束、暂停、继续的控制

            (9). sequence_repetition:               序列化执行的重复次数

            (10). start_stop:                       序列化执行的起始寄存器设置和终止寄存器设置

            (11). over_voltage_protection_value:    过压保护的电压触发值，达到对应电压后触发过压保护

            (12). over_current_protection:          过流保护是否打开

            (13). default_time_for_sequence:        默认的全局时间设置，当序列化中未设置对应时间时使用该默认时间

            (14). set_time_for_sequence:            为序列化的每一个寄存器设置电压电流对应的时间

            (15). wait:                             控制电源自身在执行命令之间的延时

            (16). get_store:                        获取11-255序列化相关寄存器的参数

            (17). get:                              获取任意或所有的电源状态信息：硬件信息、寄存器信息、显示、输出等等

            (18). tmode:                            触发输入影响输出功能

            (19). switching_signal_level:           控制输出的是上升沿还是下降沿，跟模拟接口相关

            (20). power_on:                         电源打开后，输出的状态

            (21). set_device_trigger:               设置寄存器参数，并执行

            (22). reset_device_settings:            重置设备参数

            (23). display:                          在远程模式下设置是否激活数码管的显示，当退出远程模式后数码管自动激活显示

            (24). saving_device_settings:           保存当前的设备设置参数

            (25). min_max:                          设置最小-最大电压值的保存是否激活

            (26). enable_registers:                 几个使能寄存器的设置

            (27). output_off_delay_for_ocp:         当发生过流保护时，延迟一小段时间后再关闭电源

            (28). start_self_test:                  设备自检，一般在打开电源后会自动进行

            (29). device_clear_function:            清除电脑端接口的输入输出缓存

            (30). clear_status:                     清除所有的状态寄存器（ESR, ERA, ERB），基本位于0-10寄存器

            (31). interface_address:                电源网络的控制中设备在网络中的地址，用于区分设备并进行控制

            (32). recalling_stored_settings:        调用之前保存到寄存器的设置

            (33). power_on_status_clear:            当设备关闭后清除使能寄存器

            (34). operation_complete:               同步控制器与设备之间，一般用于电源网络的使用
    """

    def __init__(self, port: str, baud_rate: int = 19200, address: str = "713"):
        self.__serial = serial_port
        self.__port = port
        self.__baud_rate = baud_rate
        self.__address = address
        self.__max_current = 20.0
        self.__max_voltage = 20.0
        self.__connected = False

    @staticmethod
    def __check_time(time: float):
        """
        检查时间是否大于0.001小于9.999
        :param time: 时间
        """
        if time < 0.001 or time > 9.999:
            raise ValueError(f"wait time: [{time}] is not supported.")

    def __send(self, cmd: str, receive: bool = False) -> str:
        """
        发送可编程电源的控制命令

        :param cmd: 命令字符串

        :param receive:
            True: 发送命令后立刻接收命令的返回信息

            False: 只发送命令，不接受任何信息，默认值
        """
        logger.debug(f">>> sending serial command to power supply: {cmd}")
        self.__serial.send(cmd, True, end='\n')
        if receive:
            contents = self.__serial.read_lines()
            result = "".join(contents)
            # result = self.__serial.read_all(False)
            logger.debug(f"<<< get power supply information from serial buffer: {result}")
            return result
        return ""

    def __header(self):
        """
        为所有命令统一增加设备地址控制命令字段
        """
        return "OUTPUT " + self.__address + ";"

    def open(self):
        """
        连接串口
        """
        self.__serial.connect(port=self.__port, baud_rate=self.__baud_rate)
        if self.get("IDN"):
            self.__connected = True

    def close(self):
        """
        所有操作结束后关闭串口端口
        """
        logger.info("closing serial port.")
        self.__serial.disconnect()

    @check_connect("__connected", battery_tips)
    def wait(self, time: float):
        """
        WAIT

        1.在执行命令之间的延时，主要是用于电源内部命令之间的延时，在wait时间内其他的命令和数据均不会被执行

        :param time:
            等待时间，浮点型，范围[0.001, 9.999]s

        :return:
            True: 设置完成

            False: 设置失败或参数错误
        """
        time = round(time, 3)
        self.__check_time(time)
        cmd = self.__header() + "WAIT " + str(time)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def tmode(self, mod: str):
        """
        T_MODE 触发输入功能选择

        :param mod:
            OFF:触发输出禁止

            OUT:触发输入影响输出

            RCL:调用寄存器内设置

            SEQ:sequence go，开始执行序列

            LLO:本地锁，面板操作禁止

            MIN:测量值的min-max寄存器操作

        :return:
            True: 设置完成

            False: 设置失败或参数错误
        """
        mod = mod.upper()
        cmd = self.__header() + "T_MODE "
        if mod in ('OFF', 'OUT', 'RCL', 'SEQ', 'LLO', 'MIN'):
            cmd = cmd + mod
        else:
            raise ValueError(f"unsupport mode: {mod}.")
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def set_time_for_sequence(self, time: float):
        """
        TSET
            1.为序列执行设置时间

            2.设置的值被保存到SETUP寄存器中作为设备设置，使用SAVE命令执行保存

        :param time:
            设置的时间，浮点型，范围[00.01, 99.99]

        :return:
            True: 设置完成

            False: 设置失败或参数错误
        """
        time = round(time, 2)
        self.__check_time(time)
        cmd = self.__header() + "TSET " + str(time)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def default_time_for_sequence(self, time: float):
        """
        TDEF
            1.当TSET未设置时间时，使用该函数设置的全局默认时间

        :param time:
            设置的全局默认时间，浮点型，范围[00.01, 99.99]

        :return:
            True: 设置完成

            False: 设置失败或参数错误
        """
        time = round(time, 2)
        self.__check_time(time)
        cmd = self.__header() + "TDEF " + str(time)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def get_store(self, start: Optional[int] = None, stop: Optional[int] = None, split: Optional[str] = None):
        """
        STORE?

        1.获取寄存器中的参数信息，其他信息的获取均使用get方法

        2.所有参数都不设置则获取寄存器中从地址从头到最后的所有寄存器参数

        3.只设置第一个参数则获取start对应地址的寄存器参数

        4.设置第1、2个参数则获取寄存器地址从start到stop的所有参数信息

        5.第3个参数split只针对第【4】种情况有效，且只能设置为tab或None

        :param start: 整形或None，范围[11, 255]

        :param stop: 整形或None，范围[11, 255]

        :param split: 分隔符，None或tab

        :return: 返回的参数字符串
        """
        cmd = self.__header() + "STORE?"
        if start:
            cmd = cmd + " " + str(start)
            if stop:
                cmd = cmd + ", " + str(stop)
                if split:
                    cmd = cmd + ", " + split
        return self.__send(cmd, receive=True)

    @check_connect("__connected", battery_tips)
    def store(self, location: int, uset: float, iset: float, tset: float, sset: str = 'ON'):
        """
        STORE

        1.将参数直接写入寄存器中

        2.写入数据时直接覆盖原有的数据

        3.寄存器的地址无偏移设置

        4.相对*SAV命令，STORE命令更快，更加面向代码级的使用

        5.[sset]参数未来可能是可选项，目前不确定事都有效，如果是可选项则会自动被忽略

        :param location: 要设置的寄存器地址，整形， 范围[11, 255]

        :param uset: 电压设置值，浮点，范围[0.000, ulimit(<=20.000)]

        :param iset: 电流设置值，浮点，范围[0.000, ilimit(<=20.000)]

        :param tset: 时间设置值，浮点，范围[00.01, 99.99] s,如果为00.00则使用rdef的值

        :param sset:
            OFF: 信号输出n个上升延

            ON: 信号输出n个下降延

            CLR: 删除整个存储空间
        """
        uset = round(uset, 3)
        iset = round(iset, 3)
        tset = round(tset, 2)
        if location < 11 or location > 255:
            raise ValueError(f"location[{location}] is out of [11,255]")
        if uset < 0 or uset > self.__max_voltage:
            raise ValueError(f"uset[{uset}] is out of [0,20]")
        if iset < 0 or iset > self.__max_current:
            raise ValueError(f"iset[{iset}] is out of [0,20]")
        if tset < 0.01 or tset > 99.99:
            raise ValueError(f"tset[{tset}] is out of [0.01,99.99]")
        cmd = self.__header() + "STORE " + str(location) + ", " + str(uset) + ", " + str(iset) + ", " + str(tset) + ", "
        sset = sset.upper()
        types = 'OFF', 'ON', 'CLR'
        if sset in types:
            cmd = cmd + sset
        else:
            raise ValueError(f"sset={sset} is not supported. only support {types}")
        self.__send(cmd)
        sleep(0.1)

    @check_connect("__connected", battery_tips)
    def switching_signal_level(self, switch: bool):
        """
        SSET

        1.切换功能信号

        :param switch:
            False: 信号输出n个上升延

            True: 信号输出n个下降延
        """

        cmd = self.__header() + "SSET "
        if switch:
            cmd = cmd + "ON"
        else:
            cmd = cmd + "OFF"
        self.__send(cmd)
        return True

    @check_connect("__connected", battery_tips)
    def start_stop(self, start: int, stop: int):
        """
        START_STOP

        1.设置序列执行的起始存储位置和终止存储位置

        :param start:序列执行的起始存储位置，整形，范围[11, 255]

        :param stop:序列执行的终止存储位置，整形，范围[11, 255]
        """

        if start < 11 or start > 255:
            raise ValueError(f"start[{start}] is out of [11,255]")
        if stop < 11 or stop > 255:
            raise ValueError(f"stop[{stop}] is out of [11,255]")
        if start >= stop:
            raise ValueError(f"start[{start}] < stop[{stop}] must be fit, nothing will be set.")
        cmd = self.__header() + "START_STOP " + str(start) + ", " + str(stop)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def sequence(self, action: str):
        """
        SEQUENCE

        1.自动按顺序调用已保存到寄存器中的设置

        :param action:
            GO: 开始序列执行

            HOLD: 暂停执行，序列暂停在当前执行位置

            CONT: 继续自动序列执行，从下一个存储位置开始

            STRT: 执行第一个可用的存储位置，输出打开，单步控制

            STEP: 执行下一个可用的存储位置

            STOP: 执行结束存储位置的参数，停止自动序列执行或单步控制
        """
        action = action.upper()
        cmd = self.__header() + "SEQUENCE "
        types = 'GO', 'HOLD', 'CONT', 'STRT', 'STEP', 'STOP'
        if action in types:
            cmd = cmd + action
        else:
            raise ValueError(f"action[{action}] is incorrect, only support{types}")
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def sequence_repetition(self, reps: int = 1):
        """
        REPETITION

        1.序列的重复次数

        :param reps:
            0: 一直重复，直到收到停止命令或手动停止

            1-255: 重复相应次数
        """
        if reps < 0 or reps > 255:
            raise ValueError(f"sequence repetition time must be >=0 and <= 255, [{reps}] is not supported.")
        if reps == 0:
            logger.debug("sequence will repeat forever.")
        else:
            logger.debug(f"sequence will repeat for {reps} times.")
        cmd = self.__header() + "REPETITION " + str(reps)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def power_on(self, status: str):
        """
        功能：POWER_ON

        1.电源开关，输出开关的状态

        :param status:
            RST: 重置到设备默认的设置

            RCL: 调用设备最后一次使用的设置

            SBY: 调用最后一次使用的设置，但输出暂时保持关闭状态
        """
        cmd = self.__header() + "POWER_ON "
        types = 'RST', 'RCL', 'SBY'
        if status in types:
            cmd = cmd + status
        else:
            raise ValueError(f"un support power_on parameter: status={status}, must be one of {types}.")
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def output_enable(self, switch: bool = True):
        """
        OUTPUT

        1.电压输出使能

        :param switch:
            True: 打开电压输出

            False: 关闭电压输出
        """
        cmd = self.__header()
        if switch:
            cmd = cmd + "OUTPUT ON"
        else:
            cmd = cmd + "OUTPUT OFF"
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def over_voltage_protection_value(self, value: float = 22.0):
        """
        OVSET

            1.过压保护设置触发电压值

            2.达到过压保护电压值后输出立刻停止

        :param value:
            过压保护触发的电压值，浮点型，范围[0, 25.000]
        """
        value = round(value, 1)
        if value < 3 or value > 25:
            raise ValueError("WARNING:protection voltage not in [3, 25] might cause damage for power consumer.")
        if value < 0 or value > 30:
            raise ValueError("protection voltage less than 0 or bigger than 30 is not supported.")
        cmd = self.__header() + "OVSET " + str(value)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def over_current_protection(self, switch: bool = True):
        """
        OCP

        1.过流保护功能

        :param switch:
            False: 过流保护功能关闭

            True: 过流保护功能打开，DELAY时间后立刻停止输出
        """
        cmd = self.__header()
        if switch:
            cmd = cmd + "OCP ON"
        else:
            cmd = cmd + "OCP OFF"
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def set_voltage(self, voltage: float = 12.0):
        """
        USET

        1.设置电压值，设置值不能大于最大限制值，否则不进行设置

        :param voltage:  要设置的电压上限值，浮点型，范围[0.000, ulimit]

        :return:
            True: 设置完成

            False: 设置失败或参数错误
        """
        voltage = round(voltage, 3)
        if voltage < 0 or voltage > self.__max_voltage:
            raise ValueError(f"voltage set must be >=0.000 and <={self.__max_voltage}, [{voltage}] is not supported.")
        cmd = self.__header() + "USET " + str(voltage)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def set_current(self, current: float = 5.0):
        """
        ISET

        1.设置电流值，设置值不能大于最大限制值，否则不进行设置

        :param current: 要设置的电流上限值，浮点型，范围[0.000, ilimit]
        """
        current = round(float(current), 3)
        if current < 0 or current > self.__max_current:
            raise ValueError(f"current set must be >=0.000 and <={self.__max_current}, [{current}] is not supported.")
        cmd = self.__header() + "ISET " + str(current)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def set_voltage_limit(self, voltage: float = 20.0):
        """
        ULIM

        1.设置电压上限值，不能低于当前实际设置的电压值，否则设置无效

        :param voltage: 要设置的电压上限值，浮点型，范围[0.000, 20.000]
        """
        voltage = round(voltage, 3)
        if voltage < 0 or voltage > 20:
            raise ValueError(f"voltage limit must be >=0.000 and <=20.000, [{voltage}] is not supported.")
        cmd = self.__header() + "ULIM " + str(voltage)
        self.__send(cmd)
        self.__max_voltage = voltage

    @check_connect("__connected", battery_tips)
    def set_current_limit(self, current: float = 20.0):
        """
        ILIM

        1.设置电流上限值，不能低于当前实际设置的电流值，否则设置无效

        :param current: 要设置的电流上限值，浮点型，范围[0.000, 20.000]
        """
        current = round(current, 3)
        if current < 0 or current > 20:
            raise ValueError(f"current limit must be >=0.000 and <=20.000, [{current}] is not supported.")
        cmd = self.__header() + "ILIM " + str(current)
        self.__send(cmd)
        self.__max_current = current

    @check_connect("__connected", battery_tips)
    def enable_registers(self, ese: Optional[int] = None, erae: Optional[int] = None, erbe: Optional[int] = None,
                         sre: Optional[int] = None, pre: Optional[int] = None):
        """
        针对这五个寄存器(ESE ERAE ERBE SRE PRE)使能

        1.使能寄存器

        2.本设备共有5个使能寄存器

        3.特定使能寄存器的位必须被首先设置，与掩码保持一致

        4.设置为0可清除寄存器

        :param ese: 事件标准使能寄存器

        :param erae: 事件使能寄存器A

        :param erbe: 事件使能寄存器B

        :param sre: 服务请求使能寄存器

        :param pre: 并行轮询使能寄存器
        """
        set_list = dict()
        if ese and 255 >= int(ese) >= 0:
            set_list['*ESE'] = int(ese)
        if erae and 255 >= int(erae) >= 0:
            set_list['ERAE'] = int(erae)
        if erbe and 255 >= int(erbe) >= 0:
            set_list['ERBE'] = int(erbe)
        if sre and 255 >= int(sre) >= 0:
            set_list['*SRE'] = int(sre)
        if pre and 255 >= int(pre) >= 0:
            set_list['*PRE'] = int(pre)
        if len(set_list) == 0:
            raise ValueError("no enable register need to be set or parameter error.")
        cmd = self.__header()
        for i, reg in enumerate(set_list):
            if i == len(set_list) - 1:
                cmd = cmd + str(reg) + " " + str(set_list[reg])
            else:
                cmd = cmd + str(reg) + " " + str(set_list[reg]) + ";"
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def display(self, switch: bool = True):
        """
        DISPLAY

        1.在远程模式下激活或禁止数码管显示

        2.如果显示处于禁止模式，需要不定时刷新

        :param switch:
            True: 显示激活

            False: 显示禁止
        """
        cmd = self.__header() + "DISPLAY "
        if switch:
            cmd = cmd + " ON"
        else:
            cmd = cmd + "OFF"
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def min_max(self, status: str = 'OFF'):
        """
        MINMAX

        1.设置最小-最大电流电压值的保存是否激活

        :param status:
            OFF: 关闭最小-最大值的保存，默认

            ON: 激活最小-最大值得保存

            RST: 重置
        """
        status = status.upper()
        cmd = self.__header() + "MINMAX "
        types = 'OFF', 'ON', 'RST'
        if status in types:
            cmd = cmd + status
        else:
            cmd = cmd + "OFF"
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def output_off_delay_for_ocp(self, delay: float):
        """
        DELAY

        1.过流保护的输出关闭延迟

        2.只有当过流保护over_current_protection功能打开时，此功能有效

        3.当实际的输出电流>=设置电流时，过流保护被触发，输出会立刻被禁止，CC指示灯不断闪烁

        4.本方法设置一个延迟窗口时间，在时间之内如果实际输出电流降回到设置电流之下，则终止过流保护，继续正常输出，
            旨在防止电流脉冲导致的频繁断电

        5.默认的时间为00.00

        :param delay:  延迟时间设置，00.00s - 99.99s
        """

        delay = round(float(delay), 2)
        self.__check_time(delay)
        cmd = self.__header() + "DELAY " + str(delay)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def device_clear_function(self):
        """
        DCL

        1.清除电脑端接口的输入输出缓存
        """
        cmd = self.__header() + "DCL"
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def interface_address(self, n: int):
        """
        ADDRESS

        1.设置总线上的设备地址（同时控制多台电源设备时可通过设备地址区分是控制的哪一台设备）

        :param n: 要设置的总线地址，整形，范围[0, 31]
        """
        if n < 0 or n > 31:
            raise ValueError(f"address must be >=0 and <= 31, [{n}] is unsupported.")
        cmd = self.__header() + "ADDRESS " + str(n)
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def start_self_test(self):
        """
        TST?

        1.设备自检

        2.自检结果可读取

        3.自检过程需要6s
        """
        cmd = self.__header() + "*TST?"
        logger.info(f">>> sending serial command to power supply: {cmd}")
        self.__serial.send(cmd, True, end='\n')
        sleep(8)
        result = self.__serial.read_all(False)
        logger.info(f"<<< get power supply information from serial buffer: {result}")
        return result == 0

    @check_connect("__connected", battery_tips)
    def saving_device_settings(self, n: int):
        """
        SAV

        1.保存设备设置

        :param n:
            寄存器中的位置，整形，范围[

            0: 清除序列sequence内存中从开始到结束位置

            1-10: 当前设备设置保存到SETUP寄存器中

            11-253: 当前参数设置保存到选择的sequence内存中相应位置

            254-255: 内存参考值]
        """
        n = int(n)
        if n < 0 or n > 255:
            raise ValueError(f"memory location must be >=0 and <=255, [{n}] is over limit.")
        cmd = self.__header() + "*SAV " + str(n)
        msg = self.__send(cmd, receive=True)
        if msg:
            logger.info(f"saving device settings has a command response: {msg}")

    @check_connect("__connected", battery_tips)
    def reset_device_settings(self):
        """
        RST

        1.重置设备设置

        默认值：

        OUTPUT OFF      输出关闭

        USET 0          电压设置0

        ISET 0          电流设置0

        OVSET max       过压保护触发值最大

        ULIM unom       电压限制值默认

        ILIM inom       电流限制值默认

        COP OFF         电流限制使用默认值

        DELAY 0         在CC模式下输出立刻禁止

        TSET 0          序列时间为默认

        SEQUENCE OFF    序列功能关闭

        DISPLAY ON      显示功能开启

        MINMAX OFF      最小最大值无记录

        TDEF            0.01s

        REPETITION      0

        START_STOP      011, 011

        POWER ON        重置不改变该状态

        T_MODE          重置不改变该状态

        DDT register    寄存器被清除
        """
        cmd = self.__header() + "*RST"
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def recalling_stored_settings(self, n: int):
        """
        RCL

        1.调用保存的设置

        :param n:

            寄存器中的位置，整形，范围[

            1-10: SETUP存储中的参数，

            11-253: SEQUENCE中的参数，

            254-255: 内存参考值]
        """
        if n < 1 or n > 255:
            raise ValueError(f"memory location must be >=1 and <=255, [{n}] is over limit.")
        cmd = self.__header() + "*RCL " + str(n)
        msg = self.__send(cmd, receive=True)
        if msg:
            logger.info(f"recalling stored settings has a command response: {msg}")

    @check_connect("__connected", battery_tips)
    def power_on_status_clear(self, clear: bool = False):
        """
        PSC/POC

        1.当设备关闭后使能寄存器是否被清除

        :param clear:
            True: 使能寄存器被清除

            False: 使能寄存器不被清除
        """
        cmd = self.__header()
        if clear:
            cmd = cmd + "*PSC 1"
        else:
            cmd = cmd + "*PSC 0"
        self.__send(cmd)

    @check_connect("__connected", battery_tips)
    def operation_complete(self, *args):
        """
        OPC， 如set_device_trigger("USET 10", "ISET 5.5")

        1.同步控制器与设备

        2.OPC命令之前需要会产生消息的其他命令组合

        3.命令执行完毕后，标准事件寄存器（ESR）会被设置为0

        4.根据使能寄存器（ESE）的掩码决定是否产生服务请求（SRQ）

        :param args: 传入要设置的命令(OPC命令会自动被附在命令最后，不需要传入)
        """
        if args:
            cmd = self.__header()
            for i, arg in enumerate(args):
                if i == len(args) - 1:
                    cmd = cmd + arg + "*OPC"
                else:
                    cmd = cmd + arg + ";"
            msg = self.__send(cmd, receive=True)
            if msg:
                logger.info(f"operation complete has a command response: {msg}")
        else:
            logger.info(f"empty parameter: [{args}], command ignored.")

    @check_connect("__connected", battery_tips)
    def set_device_trigger(self, *args):
        """
        DDT 如set_device_trigger("USET 10", "ISET 5.5", "TEST 5.00", "OUTPUT ON", "USET 2")

        1.设置一系列的命令列表，并保存到一个寄存器中，命令列表为字符串且最大长度不超过80

        2.当设备收到"TRG"命令后开始执行之前的命令列表

        :param args:传入要设置的命令(TRG命令会自动被附在命令最后，不需要传入)
        """
        if args:
            cmd = self.__header() + "*DDT "
            for i, a in enumerate(args):
                if i == len(args) - 1:
                    cmd = cmd + a + ";*TRG"
                else:
                    cmd = cmd + a + "/"
            if len(cmd) > 80 + 21:
                raise ValueError(
                    f"the length of all parameters must be smaller than 80, current length is : {len(cmd) - 21}")
            msg = self.__send(cmd, receive=True)
            if msg:
                logger.info(f"define device trigger has a command response: {msg}")
        else:
            logger.info(f"empty parameter: [{args}], command ignored.")

    def get(self, *args):
        """
        1.获取编程电源的状态信息，可获取一种或同时获取多种

        2.不传入任何参数则获取所有列表中的参数信息(获取所有信息可能需要一些时间)

        3.传入参数则获取参数对应的寄存器信息

        :param args:
            DDT: define device trigger  (定义设备触发器的寄存区命令)

            IDN: device identification  (设备id等信息：设备名、型号、总线地址、硬件版本、软件版本)

            IST: individual status query  (独立状态：0：本地消息为false，1：本地消息为true)

            LRN: complete configuration query  (完整的功能配置信息：电流、电压、时间、上限、输出、模式等)

            OPC: operation complete flag  (控制器与设备之间是否同步完成)

            PSC: power on status clear flag  (设备关闭后是否清除使能寄存器)

            STB: status byte register query  (状态字节寄存器：124>=n>=16)

            CRA: condition register query  (条件寄存器：255>=n>=0)

            DELAY: output off delay for ocp  (过流保护的输出关闭延迟)

            DISPLAY: activate/deactivate digital displays  (激活或禁止数码管显示)

            ESR: event standard regidter  (标准事件寄存器，读取后重置)

            ERA: event register A  (事件寄存器A，读取后重置)

            ERB: event register B  (事件寄存器B，读取后重置)

            ESE: event standard enable register  (标准事件使能寄存器)

            ERAE: event enable register A  (事件使能寄存器A)

            ERBE: event enable register B  (事件使能寄存器B)

            SRE: service request enable register  (服务请求使能寄存器)

            PRE: parallel poll enable register  (并发轮询使能寄存器)

            ILIM: current setting limit value  (电流上限值设置)

            IMAX: maximum measured current value  (最大测量电流值)

            IMIN: minimum measured current value  (最小测量电流值)

            IOUT: querying the momentary current value  (获取当前瞬时电流输出)

            ISET: current setpoint  (电流设置点)

            MINMAX: min-max storage for measured u and i  (测量电压电流值得保存)

            MODE: querying the momentary control mode  (获取当前控制模式：OFF：输出禁止

                                                                        CV：恒压输出模式

                                                                        CC：恒流输出模式

                                                                        OL：过载)

            OCP: over current protection  (过流保护功能状态)

            OUTPUT: activate/deactivate output  (激活或禁止电压输出)

            OVSET: over voltage protection trigger value  (过压保护触发值)

            POUT: querying the momentary power value  (获取当前的输出功率)

            POWERON: output switching status, response after power on  (电源开关，输出开关状态)

            REPEAT: number of repetitions for sequence function  (自动调用序列的重复次数)

            SEQ: automatic sequential recall of stored settings  (自动按顺序调用保存的设置)

            STA: memory location start and stop addresses for sequence function  (序列执行的起始和结束存储地址)

            SSET: switching function signal level  (切换功能信号)

            TDEF: default time for sequence function  (序列功能的默认时间)

            TMODE: trigger input function selection  (触发输入功能选择)

            TSET: dwell time specific to memory location for the sequence function  (为序列执行设置的时间)

            ULIM: voltage setting limit value  (电压设置上限值)

            UMAX: maximum measured voltage value  (最大测量电压值)

            UMIN: minimum measured voltage value  (最小测量电压值)

            UOUT: querying the momentary voltage value  (获取当前实际输出电压值)

            USET: voltage setpoint value  (设置的电压值)

            None: return all info above  (参数为空时返回以上所有类型的信息)

        :return:
            与传入参数对应的状态信息，只获取一个时返回字符串，获取多个时返回字典
        """
        queries = {'DDT': '*DDT?', 'IDN': '*IDN?', 'IST': '*IST?', 'LRN': '*LRN?', 'OPC': '*OPC?', 'PSC': '*PSC?',
                   'STB': '*STB?', 'CRA': 'CRA?', 'DELAY': 'DELAY?', 'DISPLAY': 'DISPLAY?', 'ESR': '*ESR?',
                   'ERA': 'ERA?', 'ERB': 'ERB?', 'ESE': '*ESE?', 'ERAE': 'ERAE?', 'ERBE': 'ERBE?', 'SRE': '*SRE?',
                   'PRE': '*PRE?', 'ILIM': 'ILIM?', 'IMAX': 'IMAX?', 'IMIN': 'IMIN?', 'IOUT': 'IOUT?', 'ISET': 'ISET?',
                   'MINMAX': 'MINMAX?', 'MODE': 'MODE?', 'OCP': 'OCP?', 'OUTPUT': 'OUTPUT?', 'OVSET': 'OVSET?',
                   'POUT': 'POUT?', 'POWERON': 'POWER_ON?', 'REPEAT': 'REPETITION?', 'SEQ': 'SEQUENCE?',
                   'STA': 'START_STOP?', 'SSET': 'SSET?', 'TDEF': 'TDEF?', 'TMODE': 'T_MODE?', 'TSET': 'TSET?',
                   'ULIM': 'ULIM?', 'UMAX': 'UMAX?', 'UMIN': 'UMIN?', 'UOUT': 'UOUT?', 'USET': 'USET?'}
        response = dict()
        if not args:
            for i in queries:
                cmd = self.__header() + queries[i]
                res = self.__send(cmd, receive=True)
                response[i] = res
            return response
        elif len(args) == 1:
            if args[0] in queries:
                cmd = self.__header() + queries[args[0]]
            else:
                cmd = self.__header() + args[0]
            res = self.__send(cmd, receive=True)
            return res
        else:
            for arg in args:
                if arg in queries:
                    cmd = self.__header() + queries[arg]
                else:
                    cmd = self.__header() + arg
                res = self.__send(cmd, receive=True)
                response[arg] = res
            return response

    @check_connect("__connected", battery_tips)
    def clear_status(self):
        """
        1.清除所有事件寄存器：ESR, ERA, ERB

        2.清除表示状态字节的寄存器

        3.任何请求SRQ的均被清除

        4.手动操作无效
        """
        cmd = self.__header() + "*CLS"
        self.__send(cmd)
