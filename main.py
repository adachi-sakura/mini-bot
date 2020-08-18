#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging
import threading
import signal
import sys

import robot
import pb.cs_miniserver_pb2 as cs_pb
import pb.retcode_pb2 as pb_retcode
import pb.cs_gamemessage_pb2 as game_pb
import head_pb2 as pb_head
# import pb.cs_one_pb2 as pb_one
# import pb.cs_fight_pb2 as pb_fight

robot.init_pb_module(cs_pb)

status = True


def sigHdr(sig, frame):
    global status
    print('sigint caught')
    status = False


signal.signal(signal.SIGINT, sigHdr)


async def main():
    logging.basicConfig(format='{asctime} {levelname} [{name}]: {message}',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        style='{',
                        level=logging.DEBUG)

    # robot1 = RegisterRobot('10.10.98.112', 10000, token='robot')
    # robot1 = SinglePlayRobot('10.10.98.112', 20000, token='robot')
    # robot2 = MyRobot2('10.10.98.111', 5000, token='robot2')
    robot1 = MultiPlayRobot('10.10.98.112', 10000, 'sakura', '123')
    robot2 = MultiPlayRobot('10.10.98.112', 10000, 'adachi', 'adachi')
    await asyncio.gather(robot1.run(), robot2.run())
    # await robot1.run()


class RegisterRobot(robot.Robot):
    def __init__(self, host, port, username, pwd, token='robot', timeout=10):
        super(RegisterRobot, self).__init__(host, port, token, timeout)
        self._username = username
        self._pwd = pwd

    async def _operate(self):
        register_rsp = await self._send_proto_wait_for_rsp(
            cs_pb.RegisterReq(username=self._username, password=self._pwd))
        if register_rsp.retcode == pb_retcode.RET_FAIL:
            return
        await self._send_proto_wait_for_rsp(
            cs_pb.LoginReq(username=self._username, password=self._pwd))
        # await self._send_proto_wait_for_rsp(pb_one.ModifyNicknameReq(nickname='测试123'))
        # await self._send_proto_wait_for_rsp(pb_one.GetMainDataReq())
        # self._send_proto(pb_fight.GameStartNotify())
        await asyncio.sleep(5)
        pass


class SinglePlayRobot(robot.Robot):
    def __init__(self, host, port, username, pwd, token='robot', timeout=10):
        super(SinglePlayRobot, self).__init__(host, port, token, timeout)
        self._status = 1
        self._username = username
        self._pwd = pwd

    async def _heartbeat(self):
        global status
        while self._status == 1 and status:
            self._send_proto(cs_pb.HeartbeatNotify())
            await asyncio.sleep(5)

    async def _operate(self):
        asyncio.get_event_loop().call_soon_threadsafe(self._heartbeat)
        login_rsp = await self._send_proto_wait_for_rsp(
            cs_pb.LoginReq(username=self._username, password=self._pwd))
        if login_rsp.retcode == pb_retcode.RET_FAIL:
            return

        self._uid = login_rsp.uid

        match_rsp = await self._send_and_wait_for_rsp(cs_pb.SinglePlayReq(),
                                                      rsp_name='GameMatchRsp')
        if match_rsp.retcode == pb_retcode.RET_FAIL:
            return

        game_robot = GameRobot(self._uid,
                               match_rsp.addr.ip,
                               match_rsp.addr.port,
                               roomId=match_rsp.room_id,
                               token=match_rsp.token)
        t = threading.Thread(target=game_robot.letsDoThis)
        t.start()

        global status
        while game_robot.isRun() and status:
            await asyncio.sleep(5)

        t.join()

        # await self._send_proto_wait_for_rsp(pb_one.ModifyNicknameReq(nickname='测试123'))
        # await self._send_proto_wait_for_rsp(pb_one.GetMainDataReq())
        # self._send_proto(pb_fight.GameStartNotify())
        pass


class MultiPlayRobot(robot.Robot):
    def __init__(self, host, port, username, pwd, token='robot', timeout=10):
        super(MultiPlayRobot, self).__init__(host, port, token, timeout)
        self._status = 1
        self._username = username
        self._pwd = pwd

    async def _heartbeat(self):
        global status
        while self._status == 1 and status:
            self._send_proto(cs_pb.HeartbeatNotify())
            await asyncio.sleep(5)

    async def _operate(self):
        asyncio.get_event_loop().call_soon_threadsafe(self._heartbeat)
        login_rsp = await self._send_proto_wait_for_rsp(
            cs_pb.LoginReq(username=self._username, password=self._pwd))
        if login_rsp.retcode == pb_retcode.RET_FAIL:
            return

        self._uid = login_rsp.uid

        match_rsp = await self._send_and_wait_for_rsp(cs_pb.MatchReq(
            tank_type=1, valkyrie_type=1),
                                                      rsp_name='GameMatchRsp')
        if match_rsp.retcode == pb_retcode.RET_FAIL:
            return

        game_robot = GameRobot(self._uid,
                               match_rsp.addr.ip,
                               match_rsp.addr.port,
                               roomId=match_rsp.room_id,
                               token=match_rsp.token)
        t = threading.Thread(target=game_robot.letsDoThis)
        t.start()

        global status
        while game_robot.isRun() and status:
            await asyncio.sleep(5)

        t.join()

        # await self._send_proto_wait_for_rsp(pb_one.ModifyNicknameReq(nickname='测试123'))
        # await self._send_proto_wait_for_rsp(pb_one.GetMainDataReq())
        # self._send_proto(pb_fight.GameStartNotify())
        pass


class GameRobot(robot.Robot):
    def __init__(self, uid, host, port, roomId, token='robot', timeout=10):
        super(GameRobot, self).__init__(host, port, token, timeout)
        self._roomId = roomId
        self._status = 1
        self._uid = uid

    async def _heartbeat(self):
        global status
        while self._status == 1 and status:
            self._send_proto(cs_pb.HeartbeatNotify())
            await asyncio.sleep(5)

    def letsDoThis(self):
        asyncio.new_event_loop().run_until_complete(self.run())

    async def _operate(self):
        asyncio.get_event_loop().call_soon_threadsafe(self._heartbeat)
        head = pb_head.PacketHead()
        head.user_id = self._uid
        self._send_proto_with_head(
            head, cs_pb.JoinRoomReq(room_id=self._roomId, token=self._token))

        # todo 可能存在在推入等待队列前已接收到回复
        room_info = await self._wait_for_rsp('RoomInfoNotify')
        if None == room_info:
            self._status = 0
            return

        self._send_proto(cs_pb.ClientReadyNotify())
        # await self._send_proto_wait_for_rsp(pb_one.ModifyNicknameReq(nickname='测试123'))
        # await self._send_proto_wait_for_rsp(pb_one.GetMainDataReq())
        # self._send_proto(pb_fight.GameStartNotify())
        global status
        while status:
            await asyncio.sleep(5)
        self._status = 0
        pass

    def isRun(self):
        return self._status == 1


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
