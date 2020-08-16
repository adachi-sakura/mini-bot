# -*- coding: utf-8 -*-
"""
机器人，不保证稳定性，仅供开发测试用
"""
import asyncio
import collections
import hashlib
import logging
import struct
from typing import *

import head_pb2 as pb_head
import pb.cs_one_pb2 as pb_one
import pb.retcode_pb2 as pb_retcode

logger = logging.getLogger(__name__)

# 封包魔数
HEADER_MAGIC = 0x01234567
TAIL_MAGIC = 0x89ABCDEF

# 封包定义
PACKET_HEADER_STRUCT = struct.Struct('!I2HI')
PacketHeader = collections.namedtuple('PacketHeader', (
    'head_magic',
    'cmd_id',
    'head_len',
    'body_len'
))
PACKET_TAIL_STRUCT = struct.Struct('!I')
PacketTail = collections.namedtuple('PacketTail', (
    'tail_magic'
))

cmd_id_class_map = {}
cmd_name_id_map = {}


def init_pb_module(module):
    """使用新的protobuf模块需要调用这个"""
    for cmd_name in module.DESCRIPTOR.message_types_by_name:
        if not (cmd_name.endswith('Req') or cmd_name.endswith('Rsp') or cmd_name.endswith('Notify')):
            continue
        cmd_cls = getattr(module, cmd_name, None)
        if cmd_cls is None:
            continue
        cmd_id = getattr(module, 'Cmd' + cmd_name, None)
        if cmd_id is None:
            continue
        cmd_id_class_map[cmd_id] = cmd_cls
        cmd_name_id_map[cmd_name] = cmd_id


init_pb_module(pb_one)


class RobotBase:
    """实现机器人需要的最少功能"""

    def __init__(
        self, host, port, token='robot', timeout=10
    ):
        # 机器人信息
        self._host = host
        self._port = port
        self._token = token
        self._uid = 0
        self._timeout = timeout

        # 网络
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._receive_coroutine_future: Optional[asyncio.Future] = None
        # rsp CMD_ID -> Queue -> Future
        self._waiting_rsp_futures_queues: Dict[int, asyncio.Queue] = {}

    async def run(self):
        try:
            if not await self._login():
                self._log('token=%s, 登录失败', self._token)
                return
            await self._operate()
        finally:
            await self._logout()
            if self._receive_coroutine_future is not None:
                await self._receive_coroutine_future
                self._receive_coroutine_future = None
            self._reader = self._writer = None

    async def _login(self):
        # 连接
        try:
            self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        except ConnectionRefusedError:
            return False
        self._receive_coroutine_future = asyncio.ensure_future(self._receive_coroutine())

        # 认证
        auth_req = pb_one.PlayerAuthReq(
            token=self._token
        )
        auth_rsp = await self._send_proto_wait_for_rsp(auth_req)
        if auth_rsp.retcode != pb_retcode.RET_SUCC:
            return False
        self._uid = auth_rsp.uid

        # 登录
        login_req = pb_one.PlayerLoginReq()
        login_rsp = await self._send_proto_wait_for_rsp(login_req)
        if login_rsp.retcode != pb_retcode.RET_SUCC:
            return False
        return True

    async def _logout(self):
        if self._writer is None:
            return
        self._writer.close()
        await self._writer.wait_closed()

    async def _operate(self):
        # 由子类实现
        pass

    async def _receive_coroutine(self):
        while True:
            try:
                header = await self._reader.readexactly(PACKET_HEADER_STRUCT.size)
                header = PacketHeader(*PACKET_HEADER_STRUCT.unpack(header))
                body = await self._reader.readexactly(header.body_len)
                tail = await self._reader.readexactly(PACKET_TAIL_STRUCT.size)
                _tail = PacketTail(*PACKET_TAIL_STRUCT.unpack(tail))
            except (asyncio.IncompleteReadError, struct.error):
                # 已断开
                break

            cmd_id = header.cmd_id
            self._log(f'Received cmd_id=%d, %s', cmd_id, self._get_cmd_name(cmd_id), level=logging.DEBUG)

            # pop等待队列
            queue = self._waiting_rsp_futures_queues.get(cmd_id, None)
            if queue is None:
                continue
            try:
                future = queue.get_nowait()
            except asyncio.QueueEmpty:
                self._waiting_rsp_futures_queues.pop(cmd_id, None)
                continue
            if queue.empty():
                self._waiting_rsp_futures_queues.pop(cmd_id, None)
            future.set_result(body)

    @staticmethod
    def _get_cmd_name(cmd_id):
        cmd_cls = RobotBase._get_cmd_cls(cmd_id)
        if cmd_cls is None:
            return 'CmdUnknown'
        return cmd_cls.__name__

    @staticmethod
    def _get_cmd_cls(cmd_id):
        return cmd_id_class_map.get(cmd_id, None)

    @staticmethod
    def _get_cmd_id_by_proto(proto):
        return RobotBase._get_cmd_id_by_cls(type(proto))

    @staticmethod
    def _get_cmd_id_by_cls(cmd_cls):
        return RobotBase._get_cmd_id_by_name(cmd_cls.__name__)

    @staticmethod
    def _get_cmd_id_by_name(cmd_name):
        return cmd_name_id_map.get(cmd_name, 0)

    def _send_proto(self, proto):
        head = pb_head.PacketHead().SerializeToString()
        body = proto.SerializeToString()
        header = PacketHeader(
            head_magic=HEADER_MAGIC,
            cmd_id=self._get_cmd_id_by_proto(proto),
            head_len=len(head),
            body_len=len(body)
        )
        tail = PacketTail(tail_magic=TAIL_MAGIC)

        self._writer.write(PACKET_HEADER_STRUCT.pack(*header))
        self._writer.write(head)
        self._writer.write(body)
        self._writer.write(PACKET_TAIL_STRUCT.pack(*tail))

    async def _send_proto_wait_for_rsp(self, proto, log_rsp=True):
        # 获取rsp信息
        req_name = type(proto).__name__
        assert req_name.endswith('Req'), 'proto必须是Req'
        rsp_name = req_name[:-3] + 'Rsp'
        rsp_cmd_id = self._get_cmd_id_by_name(rsp_name)
        rsp_class = self._get_cmd_cls(rsp_cmd_id)

        # push等待队列
        future = asyncio.get_event_loop().create_future()
        await self._waiting_rsp_futures_queues.setdefault(rsp_cmd_id, asyncio.Queue()).put(future)

        self._send_proto(proto)
        try:
            rsp_bin = await asyncio.wait_for(future, self._timeout)
        except asyncio.TimeoutError:
            self._log('等待 %s 超时', rsp_name)
            return None

        # 解析
        rsp = rsp_class()
        rsp.ParseFromString(rsp_bin)

        if log_rsp:
            self._log(f'%s\n%s', rsp_name, rsp, level=logging.INFO if rsp.retcode == pb_retcode.RET_SUCC else logging.WARNING)
        return rsp

    def _log(self, msg, *args, level=logging.INFO, **kwargs):
        logger.log(level, f'uid=%d, {msg}', self._uid, *args, **kwargs)


class Robot(RobotBase):
    """封装一些常用的请求"""
