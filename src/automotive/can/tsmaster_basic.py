# -*- coding:utf-8 -*-
# --------------------------------------------------------
# Copyright (C), 2016-2021, philosophy, All rights reserved
# --------------------------------------------------------
# @Name:        tsmaster_basic.py
# @Author:      philosophy
# @Created:     2022/2/19 - 22:39
# --------------------------------------------------------
from ctypes import c_int, c_uint8, c_int32, c_uint64, Structure, c_ubyte, c_ulonglong

TRUE = c_int(1)
FALSE = c_int(0)

APP_CHANNEL = {
    1: c_int(0),
    2: c_int(1),
    3: c_int(2),
    4: c_int(3)
}

# TLIBCANFDControllerType
TLIBCANFDControllerType = {
    "CAN": c_int(0),
    "ISOCAN": c_int(1),
    "NonISOCAN": c_int(2)
}

TLIBCANFDControllerMode = {
    "Normal": c_int(0),  # 正常工作模式(lfdmNormal = 0),
    "ACKOff": c_int(1),  # 关闭ACK模式(lfdmACKOff = 1)
    "Restricted": c_int(2)  # 受限制模式(lfdmRestricted = 2)
}


# typedef union {
# 	u8 value;
# 	struct {
# 		u8 istx : 1;
# 		u8 remoteframe : 1;
# 		u8 extframe : 1;
# 		u8 tbd : 4;
# 		u8 iserrorframe : 1;
# 	}bits;
# }TCANProperty;

# typedef struct _TLibCAN {
# 	u8 FIdxChn;           // channel index starting from 0
# 	TCANProperty FProperties;       // default 0, masked status:
# 						  // [7] 0-normal frame, 1-error frame
# 						  // [6-3] tbd
# 						  // [2] 0-std frame, 1-extended frame
# 						  // [1] 0-data frame, 1-remote frame
# 						  // [0] dir: 0-RX, 1-TX
# 	u8 FDLC;              // dlc from 0 to 8
# 	u8 FReserved;         // reserved to keep alignment
# 	s32 FIdentifier;      // CAN identifier
# 	u64 FTimeUS;          // timestamp in us  //Modified by Eric 0321
# 	u8x8 FData;           // 8 data bytes to send
# } TLibCAN,*PLibCAN;

class TLibCAN(Structure):
    _pack_ = 1
    _fields_ = [
        ("FIdxChn", c_uint8),
        ("FProperties", c_uint8),
        ("FDLC", c_uint8),
        ("FReserved", c_uint8),
        ("FIdentifier", c_int32),
        ("FTimeUS", c_uint64),
        ("FData", c_uint8 * 8)
    ]


# typedef union {
# 	u8 value;
# 	struct {
# 		u8 EDL : 1;
# 		u8 BRS : 1;
# 		u8 ESI : 1;
# 		u8 tbd : 5;
# 	}bits;
# }TCANFDProperty;
# // CAN FD frame definition = 80 B
#   // CAN FD frame definition = 80 B
# typedef struct _TLibCANFD {
# 	u8 FIdxChn;           // channel index starting from 0        = CAN
# 	TCANProperty FProperties;       // default 0, masked status:            = CAN
# 						   // [7] 0-normal frame, 1-error frame
# 						   // [6] 0-not logged, 1-already logged
# 						   // [5-3] tbd
# 						   // [2] 0-std frame, 1-extended frame
# 						   // [1] 0-data frame, 1-remote frame
# 						   // [0] dir: 0-RX, 1-TX
# 	u8 FDLC;              // dlc from 0 to 15                     = CAN
# 	TCANFDProperty FFDProperties;      // [7-3] tbd                            <> CAN
# 						   // [2] ESI, The E RROR S TATE I NDICATOR (ESI) flag is transmitted dominant by error active nodes, recessive by error passive nodes. ESI does not exist in CAN format frames
# 						   // [1] BRS, If the bit is transmitted recessive, the bit rate is switched from the standard bit rate of the A RBITRATION P HASE to the preconfigured alternate bit rate of the D ATA P HASE . If it is transmitted dominant, the bit rate is not switched. BRS does not exist in CAN format frames.
# 						   // [0] EDL: 0-normal CAN frame, 1-FD frame, added 2020-02-12, The E XTENDED D ATA L ENGTH (EDL) bit is recessive. It only exists in CAN FD format frames
# 	s32  FIdentifier;      // CAN identifier                       = CAN
# 	u64 FTimeUS;          // timestamp in us                      = CAN
#     u8x64 FData;          // 64 data bytes to send                <> CAN
# }TLibCANFD, * PLibCANFD;

class TLibCANFD(Structure):
    _pack_ = 1
    _fields_ = [
        ("FIdxChn", c_ubyte),
        ("FProperties", c_ubyte),
        ("FDLC", c_ubyte),
        ("FFDProperties", c_ubyte),  # 0:普通can数据帧 1：canfd数据帧
        ("FIdentifier", c_int),
        ("FTimeUS", c_ulonglong),
        ("FData", c_ubyte * 64)
    ]


# typedef union
# {
# 	u8 value;
# 	struct {
# 		u8 istx : 1;
# 		u8 breaksended : 1;
# 		u8 breakreceived : 1;
# 		u8 syncreceived : 1;
# 		u8 hwtype : 2;
# 		u8 isLogged : 1;
# 		u8 iserrorframe : 1;
# 	}bits;
# }TLINProperty;
# typedef struct _TLIN {
# 	u8 FIdxChn;           // channel index starting from 0
# 	u8 FErrCode;          //  0: normal
# 	TLINProperty FProperties;       // default 0, masked status:
# 						   // [7] tbd
# 						   // [6] 0-not logged, 1-already logged
# 						   // [5-4] FHWType //DEV_MASTER,DEV_SLAVE,DEV_LISTENER
# 						   // [3] 0-not ReceivedSync, 1- ReceivedSync
# 						   // [2] 0-not received FReceiveBreak, 1-Received Break
# 						   // [1] 0-not send FReceiveBreak, 1-send Break
# 						   // [0] dir: 0-RX, 1-TX
# 	u8 FDLC;              // dlc from 0 to 8
# 	u8 FIdentifier;       // LIN identifier:0--64
# 	u8 FChecksum;         // LIN checksum
# 	u8 FStatus;           // place holder 1
# 	u64 FTimeUS;          // timestamp in us  //Modified by Eric 0321
# 	u8x8 FData;           // 8 data bytes to send
# }TLibLIN, *PLibLIN;

class TLibLIN(Structure):
    _pack_ = 1
    _fields_ = [
        ("FIdxChn", c_ubyte),
        ("FErrCode", c_ubyte),
        ("FProperties", c_ubyte),
        ("FDLC", c_uint8),
        ("FIdentifier", c_ubyte),
        ("FChecksum", c_ubyte),
        ("FStatus", c_ubyte),
        ("FTimeUS", c_ulonglong),
        ("FData", c_uint8 * 8)
    ]
