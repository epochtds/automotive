# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2020, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        konstanter_control.py
# @Author:      philosophy
# @Created:     2021/5/1 - 23:59
# --------------------------------------------------------
import math
import time
from typing import Optional

from automotive.logger.logger import logger
from .konstanter import Konstanter


class KonstanterControl(object):
    """
    Konstanter简化操作类

    1、设置电流电压的最大最小值

    使用set_limit(voltage=20.0, current=20.0)

    2、设置输出的电流电压值

    使用set_voltage_current(voltage=12.0, current=10.0)

    3、电源变动测试

      a. 设置电源变动的值到寄存器中【set_raise_down】，得到反馈的寄存器位置(start, middle, end)

      b. 调用【start】函数一次调用寄存器中的值完成电源变动

    4、整车电源电压变动测试

      a. 利用读取到的电压序列设置【set_user_voltages】到寄存器中

      b. 调用【start】函数一次调用寄存器中的值完成电源变动

    5、开启/关闭电源

    使用【output_enable】即可

    """

    def __init__(self, port: str, baud_rate: int = 19200, over_voltage: float = 22.0):
        self.__port = port
        self.__baud_rate = baud_rate
        self.__over_voltage = over_voltage
        self.__kon = Konstanter(port=self.__port, baud_rate=self.__baud_rate)

    def open(self):
        """
        打开konstanter
        """
        self.__kon.open()
        self.__kon.over_current_protection(True)
        self.__kon.output_off_delay_for_ocp(0.3)
        self.__kon.over_voltage_protection_value(self.__over_voltage)

    def close(self, output_off: bool = False):
        """
        程序执行结束后关闭输出，关闭串口

        :param output_off:
            True: 同时关闭输出

            False: 不关闭输出，保持状态
        """
        if output_off:
            self.__kon.output_enable(False)
        self.__kon.close()

    def set_limit(self, voltage: float = 20.0, current: float = 20.0):
        """
        设置电压电流的上限值

        :param voltage: 设置的电压上限值，浮点型，范围[0, 20.0]，默认值=20.0

        :param current: 设置的电流上限值，浮点型，范围[0, 20.0]，默认值=20.0
        """
        logger.debug(f"set voltage limit to {voltage} and current limit to {current}")
        self.__kon.set_current_limit(current)
        self.__kon.set_voltage_limit(voltage)

    def set_voltage_current(self, voltage: Optional[float] = None, current: Optional[float] = None):
        """
        设置输出的电压电流值

        :param voltage: 要设置的电压值，不设置则保持上次的值不修改，浮点型，范围[0, ulimit]

        :param current: 要设置的电流值，不设置则保持上次的值不修改，浮点型，范围[0, ilimit]
        """
        if voltage:
            logger.debug(f"set voltage to {voltage}")
            self.__kon.set_voltage(voltage)
        if current:
            logger.debug(f"set current to {current}")
            self.__kon.set_current(current)

    def set_raise_down(self, start: float, end: float, step: float, operator_time: float, repeat: int = 1,
                       current: int = 3) -> tuple:
        """
        设置电源的上升或下降的参数，测试电源的电压变动

        :param start: 上升或下降过程中的起点电压值

        :param end: 上升或下降过程中的终点电压值

        :param step: 上升或下降过程中的步进值

        :param operator_time: 每次上升或下降过程的时间

        :param repeat: 重复执行的次数

        :param current: 设置默认的电流

        :return: 起点电压对应的寄存器，终点电压对应的寄存器，再次回到起点电压对应的寄存器
        """
        steps = math.ceil(abs((end - start) / step))
        if start > end:
            step = step * (-1)
        mid_register = 11 + steps
        if mid_register > 255:
            mid_register = 255
        for k in range(11, mid_register):
            self.__kon.store(k, start + step * (k - 11), current, operator_time, 'ON')
        self.__kon.store(mid_register, end, current, operator_time, 'ON')
        if (255 - mid_register) > steps:
            end_register = mid_register + steps
        else:
            end_register = 255
        step = step * (-1)
        for m in range(mid_register + 1, end_register):
            self.__kon.store(m, end + step * (m - mid_register), current, operator_time, 'ON')
        if mid_register != 255:
            self.__kon.store(end_register, start, current, operator_time, 'ON')
        self.__kon.sequence_repetition(repeat)
        result = 11, mid_register, end_register
        logger.debug(
            f"power setting register:(11, {mid_register}, {end_register}) maps voltage:({start}, {end}, {start})")
        self.__kon.get_store()
        return result

    def start(self, begin: int, end: int, check_time: float = 0.01, total_time: Optional[float] = None):
        """
        执行设置好的电源参数，即依次调用寄存器， begin以及end可以通过set_user_voltages以及set_voltage_current的返回值得到

        :param begin: 设置要执行的序列的起始寄存器地址

        :param end: 设置要执行的序列的终止寄存器地址

        :param check_time: 每一次检测的间隔时间，默认时间10ms

        :param total_time: 总计超时时间

        """
        self.__kon.start_stop(begin, end)
        self.__kon.sequence('GO')
        flag = True
        logger.debug(f"total time = {total_time}")
        start_time = time.time()
        while flag:
            try:
                status = self.__kon.get('SEQ')
                tmp = status.split()[-1]
                if tmp.split(',')[0] == 'RDY' and tmp.split(',')[1] == '000':
                    flag = False
                time.sleep(check_time)
            except IndexError:
                logger.warning("konstanter response found some error")
                pass_time = time.time() - start_time
                logger.debug(f"pass time is {pass_time}")
                if total_time and pass_time > total_time:
                    flag = True
        logger.debug(f"voltage operator finished")

    def set_user_voltages(self, voltages: (list, tuple), times: int = 0.01, current: float = 5,
                          repeat: int = 1) -> tuple:
        """
        设置用户自定义的或从文件读取到的电压序列，模拟用户自定义的电压曲线

        :param voltages: 电压值列表，必须为列表或元祖类型

        :param times: 间隔时间，如果为数字则所有电压均应用该值，如果为列表则与电压voltages值一一对应

        :param current: 默认的电流设置值

        :param repeat: 电压曲线自动触发的次数

        :return: (起点电压对应的寄存器，终点电压对应的寄存器)
        """
        if not isinstance(voltages, (list, tuple)):
            self.__kon.close()
            raise ValueError(f"Voltages must be a list or tuple: {voltages}")
        if not isinstance(times, (list, tuple)):
            time_list = [times] * len(voltages)
        else:
            time_list = list(times)
            if len(time_list) < len(voltages):
                time_list = time_list + [time_list[-1]] * (len(voltages) - len(time_list))
        for i, item in enumerate(zip(voltages, time_list)):
            self.__kon.store(11 + i, item[0], current, item[1])
            if 11 + i >= 255:
                break
        registers = 11, 255
        if 11 + len(voltages) - 1 < 255:
            registers = 11, 11 + len(voltages) - 1
        self.__kon.sequence_repetition(repeat)
        self.__kon.get_store()
        return registers

    def get(self, *args):
        """
        透传Konstanter类中的get方法

        :param args: Konstanter中的get方法支持的args参数
        """
        return self.__kon.get(*args)

    def output_enable(self, switch: bool = True):
        """
        透传Konstanter类中的output_enable方法

        :param switch:
            True表示开通

            False表示关闭
        """
        self.__kon.output_enable(switch)
