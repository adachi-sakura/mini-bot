#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging

import robot
import pb.cs_miniserver_pb2 as cs_pb
import pb.retcode_pb2 as pb_retcode
# import pb.cs_one_pb2 as pb_one
# import pb.cs_fight_pb2 as pb_fight

robot.init_pb_module(cs_pb)


async def main():
    logging.basicConfig(format='{asctime} {levelname} [{name}]: {message}',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        style='{',
                        level=logging.DEBUG)

    robot1 = RegisterRobot('10.10.98.112', 10000, token='robot')
    # robot2 = MyRobot2('10.10.98.111', 5000, token='robot2')
    await asyncio.gather(robot1.run())
    # await robot1.run()


class RegisterRobot(robot.Robot):
    async def _operate(self):
        register_rsp = await self._send_proto_wait_for_rsp(
            cs_pb.RegisterReq(username='ada', password='ada'))
        if register_rsp.retcode == pb_retcode.RET_FAIL:
            pass
        await self._send_proto_wait_for_rsp(
            cs_pb.LoginReq(username='ada', password='ada'))
        # await self._send_proto_wait_for_rsp(pb_one.ModifyNicknameReq(nickname='测试123'))
        # await self._send_proto_wait_for_rsp(pb_one.GetMainDataReq())
        # self._send_proto(pb_fight.GameStartNotify())
        await asyncio.sleep(5)
        pass


class MyRobot2(robot.Robot):
    async def _operate(self):
        # await self._send_proto_wait_for_rsp(pb_one.ModifyNicknameReq(nickname='测试123'))
        # await self._send_proto_wait_for_rsp(pb_one.GetMainDataReq())
        await asyncio.sleep(5)
        pass


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
