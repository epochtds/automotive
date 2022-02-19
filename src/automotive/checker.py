# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2024, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        checker
# @Author:      philosophy
# @Created:     2022/02/19 - 22:29
# --------------------------------------------------------
import sys
from functools import wraps

from .logger import logger

can_tips = "please call method open_device first"
camera_tips = "please call method open_camera first"
connect_tips = "please call method connect first"
relay_tips = "please call method open_relay_device first"
battery_tips = "please call method open first"


def check_connect(argument: str, tips: str, is_serial: bool = False, is_bus: bool = False):
    def method(func):
        """
        检查设备是否已经连接
        """

        def wrapper(self, *args, **kwargs):
            if is_serial:
                serial = self.__dict__[f"{argument}"]
                if not (serial and serial.isOpen):
                    raise RuntimeError(tips)
            elif is_bus:
                if argument in self.__dict__:
                    flag = self.__dict__[argument]
                else:
                    flag = self.__dict__[f"_{self.__class__.__name__}{argument}"]
                if not flag.is_open:
                    raise RuntimeError(tips)
            else:
                if argument in self.__dict__:
                    flag = self.__dict__[argument]
                else:
                    flag = self.__dict__[f"_{self.__class__.__name__}{argument}"]
                if not flag:
                    raise RuntimeError(tips)
            return func(self, *args, **kwargs)

        return wrapper

    return method


def control_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            if ret == 1:
                if func.__name__ == "__init_device":
                    logger.trace(f"Method <{func.__name__}> call success, and init CAN{args[2]} success.")
                elif func.__name__ == "__start_device":
                    logger.trace(f"Method <{func.__name__}> call success, and start CAN success.")
                else:
                    logger.trace(f"Method <{func.__name__}> call success, and return success.")
                return ret
            elif ret == 0:
                raise RuntimeError(f"Method <{func.__name__}> is called, and return failed.")
            elif ret == -1:
                raise RuntimeError(f"Method <{func.__name__}> is called, and CAN is not exist.")
            else:
                raise RuntimeError(f"Method <{func.__name__}> : Unknown error.")
        except Exception:
            error = sys.exc_info()
            # logger.error('ERROR: ' + str(error[0]) + ' : ' + str(error[1]))
            raise RuntimeError(error)

    return wrapper


def tsmaster_control_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            if ret == 0:
                logger.trace(f"Method <{func.__name__}> call success, and return success.")
                return ret
            else:
                raise RuntimeError(f"Method <{func.__name__}> is called, and return failed, failed code is {ret}")
        except Exception:
            error = sys.exc_info()
            logger.error('ERROR: ' + str(error[0]) + ' : ' + str(error[1]))
            raise RuntimeError(error[1])

    return wrapper
