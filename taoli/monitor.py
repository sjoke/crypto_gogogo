# -*- coding: utf-8 -*-
import time
import datetime
from okx import monitor_once
from util import send_email


FLAG = '0' #0实仓，1模拟交易


def run():
    flag_send = False
    now = datetime.datetime.now()
    print('now: ', now)
    with open("api_keys.txt", 'r') as fp:
        for i, line in enumerate(fp.readlines()[1:]):
            try:
                arr = line.strip().split(',')
                name = arr[0]
                key, secret, passphrass = arr[1], arr[2], arr[3]
                print('---start to monitor account: ' + name)
                monitor_once(key, secret, passphrass, FLAG)
                time.sleep(3)
            except Exception as e:
                msg = 'account {} 监控发生异常,请查看后台日志'.format(name)
                send_email('帐户监控异常', msg)
                raise e
        if not flag_send and now.hour == 8:
            # 每天8时，发送一次
            send_email('所有帐户正常监控', '所有帐户正常监控')
            flag_send = True
        if flag_send and now.hour > 8:
            flag_send = False


def main():
    while True:
        run()
        print('sleep 5s')
        time.sleep(5)


if __name__ == '__main__':
    main()