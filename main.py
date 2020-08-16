#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import logging

import robot
import pb.cs_one_pb2 as pb_one
import pb.cs_fight_pb2 as pb_fight


robot.init_pb_module(pb_fight)


async def main():
    logging.basicConfig(format='{asctime} {levelname} [{name}]: {message}', datefmt='%Y-%m-%d %H:%M:%S', style='{',
                        level=logging.DEBUG)

    robot1 = MyRobot1('10.10.98.111', 5000, token='robot')
    robot2 = MyRobot2('10.10.98.111', 5000, token='robot2')
    await asyncio.gather(robot1.run(), robot2.run())
    # await robot1.run()


class MyRobot1(robot.Robot):
    async def _operate(self):
        # await self._send_proto_wait_for_rsp(pb_one.ModifyNicknameReq(nickname='测试123'))
        # await self._send_proto_wait_for_rsp(pb_one.GetMainDataReq())
        self._send_proto(pb_fight.GameStartNotify())
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
