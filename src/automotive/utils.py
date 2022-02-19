# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2020, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        utils.py
# @Author:      philosophy
# @Created:     2022/2/16 - 13:35
# --------------------------------------------------------
import hashlib
import json
import time
import platform
import os
import subprocess as sp
from datetime import datetime, date
from typing import List, Tuple, Dict

import yaml

from .logger import logger


def convert_datetime_string(date_time: datetime, fmt: str = '%Y%m%d_%H%M%S') -> str:
    """
    转换时间为字符串
    usage:
        convert_datetime_string(datetime.now())

    :param date_time: 时间

    :param fmt: 转换格式

    :return 时间字符串
    """

    return date_time.strftime(fmt)


def convert_string_datetime(date_time: str, fmt: str = '%Y%m%d_%H%M%S') -> datetime:
    """
    转换字符串为时间
    usage:
        convert_string_datetime("20210112_144238")

    :param date_time: 时间字符串

    :param fmt: 转换格式

    :return: 时间(datetime数据类型)
    """
    return datetime.strptime(date_time, fmt)


def get_time_as_string(fmt: str = '%Y%m%d_%H%M%S') -> str:
    """
    返回当前系统时间，类型为string
    usage:
        get_time_as_string()   返回202202161343

    :param fmt: 格式化类型 如'%Y-%m-%d_%H-%M-%S'

    :return: 当前系统时间，如：2018-07-27_14-18-59
    """
    return time.strftime(fmt, time.localtime(time.time()))


def get_date_from_string(date_time: str, fmt: str = '%Y%m%d_%H%M%S') -> date:
    """
    根据日期字符串返回时间
    usage:
       get_date_from_string()  返回date的

    :param date_time: 时间字符串

    :param fmt: 格式化类型

    :return 时间信息
    """
    return datetime.strptime(date_time, fmt).date()


def get_week(self, date_time: str, fmt: str = '%Y%m%d') -> int:
    """
    获取当前是第几周
    :param self:
    :param date_time:
    :param fmt:
    :return:
    """
    year, week, week_of_day = self.get_date_from_string(date_time, fmt).isocalendar()
    return week


def exec_command(command: str, workspace: str = None, sub_process: bool = True) -> int:
    """
    执行命令, 涉及到bat命令的时候，都需要使用os.system的方式执行，否则会出问题

    usage:
        exec_command("ls -l", "/mnt/d")

    :param command: 命令

    :param workspace: 工作目录

    :param sub_process: 是否以子进程方式运行

    :return: 执行成功的结果，由于os.system没有，则永远返回0
    """
    logger.debug(f"it will execute command[{command}]")
    is_shell = False if platform.system() == "Windows" else True
    if sub_process:
        logger.trace("it use subprocess type")
        if workspace:
            logger.debug(f"cwd is [{workspace}]")
            p = sp.Popen(command, shell=is_shell, cwd=workspace, universal_newlines=True)
        else:
            p = sp.Popen(command, shell=is_shell, universal_newlines=True)
        p.communicate()
        return p.returncode
    else:
        logger.trace("it use os.system type")
        if workspace:
            os.chdir(workspace)
        os.system(command)
        return 0


def exec_commands(commands: List, workspace: str = None, sub_process: bool = True):
    """
    批量执行命令
    usage:
        commands = ["ls -l", "pwd"]
        exec_commands(commands, "/mnt/d")

    :param commands: 命令列表

    :param workspace: 工作目录

    :param sub_process: 否以子进程方式运行
    """
    for command in commands:
        exec_command(command, workspace, sub_process)


def exec_command_with_echo(command: str, workspace: str = None, encoding: str = "utf-8") -> Tuple:
    """
    有输出的执行
    usage:
        out, err = exec_command_with_echo("ls -l", "/mnt")

    :param command:  命令

    :param workspace: 工作目录

    :param encoding 编码格式，默认utf-8， 中文建议用gbk或者GB18030

    :return: 输出的值
    """
    logger.debug(f"it will execute command[{command}]")
    is_shell = False if platform.system() == "Windows" else True
    if workspace:
        logger.debug(f"cwd is [{workspace}]")
        p = sp.Popen(command, shell=is_shell, cwd=workspace, stdout=sp.PIPE, stderr=sp.PIPE)
    else:
        p = sp.Popen(command, shell=is_shell, stdout=sp.PIPE, stderr=sp.PIPE)
    stdout, stderr = p.communicate()
    if encoding != "":
        return stdout.decode(encoding), stderr.decode(encoding)
    else:
        return stdout, stderr


def check_file_exist(file: str):
    """
    检查文件是否存在，当路径不存在的时候会抛出异常
    usage:
        check_file_exist("/mnt/d/a.txt")

    :param file: 文件
    """
    if not (os.path.exists(file) and os.path.isfile(file)):
        raise RuntimeError(f"file[{file}] is not exist or not a file")


def check_folder_exist(folder: str):
    """
    检查路径是否存在， 当路径不存在的时候会抛出异常
    usage:
       check_folder_exist("/mnt/d“)

    :param folder: 文件夹名称
    """
    if not (os.path.exists(folder) and os.path.isdir(folder)):
        raise RuntimeError(f"folder[{folder}] is not exist or not a folder")


def delete_file(file_name: str):
    """
    删除文件
    usage:
        delete_file("/mnt/d/a.txt")
    :param file_name: 文件的完整路径名
    """
    check_file_exist(file_name)
    flag = True
    if platform.system() == "Windows":
        cmd = f"del \"{file_name}\""
        flag = False
    else:
        cmd = f"rm -rvf {file_name}"
    exec_command(cmd, sub_process=flag)


def delete_folder(folder_name: str):
    """
    删除文件夹
    usage:
        delete_file("/mnt/d/test")

    :param folder_name: 文件夹名称
    """
    check_folder_exist(folder_name)
    flag = True
    if platform.system() == "Windows":
        cmd = f"rd /Q /S \"{folder_name}\""
        flag = False
    else:
        cmd = f"rm -rvf {folder_name}"
    exec_command(cmd, sub_process=flag)


def get_hash_value(content: str) -> str:
    """
    获取字符串的哈希值

    :param content: 字符串内容

    :return:  字符串哈希值
    """
    return hashlib.md5(content.encode(encoding='UTF-8')).hexdigest()


def get_json_obj(file: str, encoding: str = "utf-8") -> Dict:
    """
    获取json文件中object对象

    :param encoding: 编码方式

    :param file: json文件的路径

    :return: json文件中的object对象
    """
    logger.debug(f"file is {file}")
    with open(file, "r", encoding=encoding) as fp:
        content = json.load(fp)
        logger.trace(f"content is {content}")
        return content


def read_yml_full(file: str, encoding: str = "UTF-8") -> Dict:
    """
    读取yml文件中的内容(full_load方法)

    :param file: yml文件的绝对路径

    :param encoding: 编码格式，默认UTF-8

    :return: yml对象对应的字典对象
    """
    logger.debug(f"file is {file}")
    with open(file, "r", encoding=encoding) as fp:
        content = yaml.full_load(fp)
        logger.debug(f"content is {content}")
        return content
