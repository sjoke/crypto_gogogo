from binance.spot import Spot
from binance.um_futures import UMFutures
from binance.cm_futures import CMFutures
import pandas as pd
import datetime
import requests

spot_client = Spot()
um_futures_client = UMFutures()
cm_futures_client = CMFutures()
spot_client.ping()
um_futures_client.ping()


def convert(long):
    t = datetime.datetime.fromtimestamp(long/1000)
    return t.strftime('%Y-%m-%d %H:%M:%S')

# 包含所有币本位合约
resp = cm_futures_client.exchange_info()
for row in resp['symbols']:
    symbol = row['symbol']
    if symbol.endswith('PERP'):
        print(symbol)
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
        df = pd.DataFrame(res)
        df.to_csv('/Users/jiaokeshi/Workspace/quant_campaign/docs/历史资金费_{}.csv'.format(symbol), index=False)
        # break


# resp = requests.get('https://dapi.binance.com/dapi/v1/fundingRate?symbol=BTCUSD_PERP&limit=1000')

# import pandas as pd

