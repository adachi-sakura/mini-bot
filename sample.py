#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一个机器人例程
"""
import asyncio
import logging

import robot
import pb.cs_one_pb2 as pb_one


async def main():
    logging.basicConfig(format='{asctime} {levelname} [{name}]: {message}', datefmt='%Y-%m-%d %H:%M:%S', style='{',
                        level=logging.DEBUG)

    # 一个机器人
    robot = MyRobot('10.10.98.111', 5000, token='robot')
    await robot.run()

    # # 并发多个机器人
    # robots = [
    #     MyRobot('10.10.98.111', 5000, token=f'robot_{i + 1}')
    #     for i in range(3)
    # ]
    # coroutines = [robot_.run() for robot_ in robots]
    # await asyncio.gather(*coroutines)


class MyRobot(robot.Robot):
    async def _operate(self):
        pass

        # Python protobuf教程：
        # https://developers.google.com/protocol-buffers/docs/pythontutorial#writing-a-message
        # https://googleapis.dev/python/protobuf/latest/


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
