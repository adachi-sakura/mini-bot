#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编译proto到py的脚本
需要安装protoc 3.0以上版本，并把protoc所在目录添加到PATH环境变量
https://github.com/protocolbuffers/protobuf/releases
"""
import glob
import os
import subprocess
import sys

ROBOT_PATH = os.path.dirname(os.path.realpath(__file__))
COMMON_PATH = os.path.realpath(os.path.join(ROBOT_PATH, '..', '..', 'common'))
PB_PATH = os.path.join(COMMON_PATH, 'pb')


def main():
    proto_path_list = glob.glob(os.path.join(PB_PATH, '*.proto'))
    process = subprocess.run(['protoc', f'-I={COMMON_PATH}', f'--python_out={ROBOT_PATH}', *proto_path_list])
    if process.returncode != 0:
        print('protoc failed', file=sys.stderr)
        return


if __name__ == '__main__':
    main()
