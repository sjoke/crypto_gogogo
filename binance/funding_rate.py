from binance.spot import Spot
from binance.um_futures import UMFutures
from binance.cm_futures import CMFutures
import pandas as pd
import datetime
import os
import json

spot_client = Spot()
um_futures_client = UMFutures()
cm_futures_client = CMFutures()
spot_client.ping()
um_futures_client.ping()


def convert(long):
    t = datetime.datetime.fromtimestamp(long/1000)
    return t.strftime('%Y-%m-%d %H:%M:%S')


s = datetime.datetime.today()
dt = s.strftime('%Y%m%d_%H%M%S')
f = os.path.join('data','币安_历史资金费_{}.csv'.format(dt))
# if not os.path.exists(folder):
#     os.mkdir(folder)
print('保存路径: ', f)
# 包含所有币本位合约
resp = cm_futures_client.exchange_info()
with open('data/cm_exchange_info.json', 'w') as fp:
    json.dump(resp, fp)

dfs = []
cnt = 0
for row in resp['symbols']:
    symbol = row['symbol']
    if symbol.endswith('PERP') and row['contractStatus'] == 'TRADING':
        print('正在获取: ', symbol)
        
        # 永续合约
        r = cm_futures_client.funding_rate(symbol, limit=1000)
        res = []
        for row in r:
            d = {
                'symbol': row['symbol'],
                'fundingTime': row['fundingTime'],
                'time':  convert(row['fundingTime']),
                'fundingRate': row['fundingRate'],
                # 'markPrice': row['markPrice'],
            }
            res.append(d)
        cnt += 1
        df = pd.DataFrame(res)
        dfs.append(df)
df = pd.concat(dfs)
df = df.sort_values('time', ascending=False)
df.to_csv(f, index=False)

print('----全部获取完成, 共{}个币种----'.format(cnt))