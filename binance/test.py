# from backend import API

# key = 'U8ZUqC5bIwbVFEubUUHjzt4k0svJUsX2ej2fVYouCbRLt7aisyLCwz5q6CkxQiwl'
# secret = 'CIj5gL9aN8qe3DZHkh0fKaH3wNtOxmyA7HKQhf0RWcYZq0PXyG9AMVF6hW9RicbR'

# api = API(key, secret)

# 查询现货持仓
# res = api.other_client.wallet.set_asset_getUserAsset()
# 统一账户查询持仓
# self.pm_client.account.get_balance()
currency = 'DOT'
amount = 100
symbol = 'BTCUSD_PERP'
side = 'BUY'

# res = api.query_pm_balance('BTC')
# res = api.open(currency, amount)
# res = api.close(currency, amount)
# res = api.check_pos_balance(currency)
# res = api.query_pm_cm_account(symbol)
# res = api.margin_trade(currency, 99.1729296, 'SELL')
# res = api.spot_client.account.get_account()
# print(res)

# res = api.pm_client.setOrder.set_cm_order(symbol=symbol, side='SELL', positionSide='LONG', type='MARKET', quantity=1)
# print(res)

# res = api.query_pm_balance('BTC')
# print(res)

# res = api.margin_trade('ETH', amount=20, side='BUY')
# res = api.spot_client.trade.set_order(symbol='BNBUSDT', side='BUY', type='MARKET', quoteOrderQty=8)
# print(res)

# 查询账户资产
# api.query_account_asset()

a = 1
d = {a
}
print(d)