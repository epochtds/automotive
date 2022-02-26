# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2020, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        serial_utils.py
# @Author:      philosophy
# @Created:     2021/5/1 - 23:34
# --------------------------------------------------------
import time
from time import sleep
from typing import List, Optional, Union

from .serial_port import SerialPort
from ..logger import logger
from .utils import SystemTypeEnum


serial_port = SerialPort()


def connect(port: str, baud_rate: int = 115200, log_folder: Optional[str] = None):
    """
    连接端口

    :param port: 串口号

    :param baud_rate: 波特率

    :param log_folder: 文件存放位置
    """
    serial_port.connect(port, baud_rate, log_folder=log_folder)


def disconnect():
    """
    断开连接
    """
    serial_port.disconnect()


def flush(flush_type: int = 0):
    """
    清空缓存
    :param flush_type:
    """
    if flush_type == 1:
        serial_port.flush_input()
    elif flush_type == 2:
        serial_port.flush_output()
    else:
        serial_port.flush_all()


def write(command: str):
    """
    写入文件
    :param command: 命令
    """
    serial_port.send(command)


def read() -> str:
    """
    读取所有内容
    """
    return serial_port.read_all()


def read_lines() -> List[str]:
    """
    读取内容
    """
    return serial_port.read_lines()


def file_exist(file: str, check_times: Optional[int] = None, interval: float = 0.5,
               timeout: int = 10) -> bool:
    if check_times:
        for i in range(check_times):
            serial_port.send(f"ls -l {file}")
            result = serial_port.read_all()
            logger.debug(f"read content is {result}")
            if "No such file or directory" not in result:
                logger.debug(f"{file} is exist")
                return True
            else:
                sleep(interval)
    # 没有check_time 即 check_time = None
    else:
        flag = True
        logger.debug(f"check_time is {check_times}, 进入超时处理")
        start = time.time()
        while flag:
            serial_port.send(f"ls -l {file}")
            result = str(serial_port.read_all())
            logger.debug(f"read content is {result}")
            # 能找到此文件
            if "No such file or directory" not in result:
                logger.debug(f"{file} is exist")
                return True
            end = time.time()
            if end - start >= timeout:
                logger.debug(f"time difference is {str(end - start)},大于规定的 {str(timeout)}， 无法找到{file}")
                flag = False
    logger.debug(f"{file} is not exist")
    return False


def copy_file(remote_folder: str, target_folder: str, system_type: Union[str, SystemTypeEnum], timeout: float = 300):
    """
    拷贝远程文件夹下所有的文件到目标文件夹下,由于是非阻塞式的，所以有超时考虑

    :param timeout: 超时时间

    :param system_type: 类型

    :param remote_folder: 远程文件夹

    :param target_folder: 拷贝的文件夹
    """
    if isinstance(system_type, str):
        system_type = SystemTypeEnum.from_value(system_type)
    flag = True
    # 清空之前的数据
    serial_port.flush()
    # 记录运行时间
    start_time = time.time()
    # 前台拷贝
    copy_command = f"cp -rv {remote_folder}/* {target_folder}"
    serial_port.send(f"{copy_command} &")
    command = f"ps -ef | grep cp" if system_type == SystemTypeEnum.LINUX else f"pidin | grep cp"
    while flag:
        serial_port.send(command)
        result = serial_port.read_all()
        logger.debug(f"result is {result}")
        if "Done" in result and copy_command in result:
            logger.info(f"copy is finished")
            flag = False
        current_time = time.time()
        if (current_time - start_time) > timeout * 1000:
            logger.info(f"copy is continue {timeout} second, but not finished")
            flag = False
        sleep(1)


def login(username: str, password: str, double_check: bool = False, login_locator: str = "login"):
    """
    登陆系统

    :param login_locator: 登陆检查标识符

    :param username: 用户名

    :param password: 密码

    :param double_check: 二次确认
    """
    flush_output = 2
    flush(flush_output)
    write("\r\n")
    sleep(0.5)
    output = read()
    if login_locator in output:
        logger.debug(f"input login username[{username}]")
        write(username)
        sleep(1)
        output = read()
        if "Password" in output or "password" in output:
            logger.debug(f"input login password[{password}]")
            write(password)
    if double_check:
        # 再次校验是否登陆成功
        flush(flush_output)
        write("\r\n")
        sleep(0.5)
        output = read()
        if "login" in output:
            logger.warning("login failed")
