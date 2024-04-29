import datetime
import requests


def convert(long):
    t = datetime.datetime.fromtimestamp(long/1000)
    return t.strftime('%Y-%m-%d %H:%M:%S')


resp = requests.get('https://dapi.binance.com/dapi/v1/fundingRate?symbol=BTCUSD_PERP&limit=1000')
res = []
for row in resp.json():
    d = {
        'symbol': row['symbol'],
        'fundingTime': row['fundingTime'],
        'time':  convert(row['fundingTime']),
        'fundingRate': row['fundingRate'],
        'markPrice': row['markPrice'],
    }
    res.append(d)

import json
import pandas as pd


df = pd.DataFrame(res)
df.to_csv('BTC_PERP.csv', index=False)