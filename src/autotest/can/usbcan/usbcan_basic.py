# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2021, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        usbcan_basic.py
# @Author:      philosophy
# @Created:     2022/2/19 - 22:39
# --------------------------------------------------------
from ctypes import c_ubyte, c_ushort, c_char, c_uint, Structure

# ===============================================================================
# 定义数据类型


UBYTE = c_ubyte
USHORT = c_ushort
CHAR = c_char
UINT = c_uint
DWORD = c_uint
BYTE = c_ubyte
UCHAR = c_ubyte
# ===============================================================================
# 定义波特率对应的Timing0和Timing1的取值
band_rate_list = {
    #   波特率  Timing0 Timing1
    10: (0x31, 0x1C),
    20: (0x18, 0x1C),
    40: (0x87, 0xFF),
    50: (0x09, 0x1C),
    80: (0x83, 0xFF),
    100: (0x04, 0x1C),
    125: (0x03, 0x1C),
    200: (0x81, 0xFA),
    250: (0x01, 0x1C),
    400: (0x80, 0xFA),
    500: (0x00, 0x1C),
    666: (0x80, 0xB6),
    800: (0x00, 0x16),
    1000: (0x00, 0x14),
    33.33: (0x09, 0x6F),
    66.66: (0x04, 0x6F),
    83.33: (0x03, 0x6F)
}


# ===============================================================================
# 定义结构体
# 包含USB-CAN系列接口卡的设备信息，结构体将在VCI_ReadBoardInfo函数中被填充
class VciBoardInfo(Structure):
    _fields_ = [
        # 硬件版本号，用16进制表示。比如0x0100表示V1.00。
        ('hw_Version', USHORT),
        # 固件版本号， 用16进制表示。比如0x0100表示V1.00
        ('fw_Version', USHORT),
        # 驱动程序版本号， 用16进制表示。比如0x0100表示V1.00。
        ('dr_Version', USHORT),
        # 接口库版本号， 用16进制表示。比如0x0100表示V1.00。
        ('in_Version', USHORT),
        # 保留参数。
        ('irq_Num', USHORT),
        # 表示有几路CAN通道。
        ('can_Num', BYTE),
        # 此板卡的序列号。
        ('str_Serial_Num', CHAR * 20),
        # 硬件类型，比如“USBCAN V1.00”（注意：包括字符串结束符’\0’）
        ('str_hw_Type', CHAR * 40),
        # 系统保留。
        ('Reserved', USHORT)
    ]


# CAN帧结构体，即1个结构体表示一个帧的数据结构。
# 在发送函数VCI_Transmit和接收函数VCI_Receive中，被用来传送CAN信息帧
class VciCanObj(Structure):
    _fields_ = [
        # 帧ID。 32位变量，数据格式为靠右对齐。
        ('id', UINT),
        # 设备接收到某一帧的时间标识。 时间标示从CAN卡上电开始计时，计时单位为0.1ms。
        ('time_stamp', UINT),
        # 是否使用时间标识，为1时TimeStamp有效， TimeFlag和TimeStamp只在此帧为接收帧时有意义。
        ('time_flag', BYTE),
        # 发送帧类型。
        # 0时为正常发送（发送失败会自动重发，重发最长时间为1.5-3秒）；
        # 1时为单次发送（只发送一次，不自动重发）；
        ('send_type', BYTE),
        # 是否是远程帧。 =0时为为数据帧， =1时为远程帧（数据段空）
        ('remote_flag', BYTE),
        # 是否是扩展帧。 =0时为标准帧（11位ID）， =1时为扩展帧（29位ID）。
        ('extern_flag', BYTE),
        # 数据长度 DLC (<=8)，即CAN帧Data有几个字节。约束了后面Data[8]中的有效字节。
        ('data_len', BYTE),
        # CAN帧的数据。由于CAN规定了最大是8个字节，所以这里预留了8个字节的空间
        # 受DataLen约束。如DataLen定义为3，即Data[0]、 Data[1]、 Data[2]是有效的。
        ('data', BYTE * 8),
        # 系统保留。
        ('reserved', BYTE * 3)
    ]


# 定义了初始化CAN的配置。结构体将在VCI_InitCan函数中被填充，
# 即初始化之前，要先填好这个结构体变量
class VciInitConfig(Structure):
    _fields_ = [
        # 验收码。 SJA1000的帧过滤验收码。对经过屏蔽码过滤为“有关位”进行匹配，全部匹
        # 配成功后，此帧可以被接收。否则不接收。
        ('AccCode', DWORD),
        # 屏蔽码。 SJA1000的帧过滤屏蔽码。对接收的CAN帧ID进行过滤，对应位为0的是“有
        # 关位”，对应位为1的是“无关位”。屏蔽码推荐设置为0xFFFFFFFF，即全部接收
        ('AccMask', DWORD),
        # 保留
        ('Reserved', DWORD),
        # 滤波方式，允许设置为0-3
        # 0/1 接收所有类型 滤波器同时对标准帧与扩展帧过滤
        # 2 只接收标准帧  滤波器只对标准帧过滤，扩展帧将直接被滤除
        # 3 只接收扩展帧  滤波器只对扩展帧过滤， 标准帧将直接被滤除
        ('Filter', UCHAR),
        # 波特率定时器 0（BTR0）。
        ('Timing0', UCHAR),
        # 波特率定时器 1（BTR1）。
        ('Timing1', UCHAR),
        # 模式。
        # =0表示正常模式（相当于正常节点），
        # =1表示只听模式（只接收，不影响总线），
        # =2表示自发自收模式（环回模式）
        ('Mode', UCHAR)
    ]
