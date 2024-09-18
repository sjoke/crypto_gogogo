from backend import API
import json

key = 'U8ZUqC5bIwbVFEubUUHjzt4k0svJUsX2ej2fVYouCbRLt7aisyLCwz5q6CkxQiwl'
secret = 'CIj5gL9aN8qe3DZHkh0fKaH3wNtOxmyA7HKQhf0RWcYZq0PXyG9AMVF6hW9RicbR'

api = API(key, secret)

# 查询现货持仓
# res = api.other_client.wallet.set_asset_getUserAsset()
# 统一账户查询持仓
# self.pm_client.account.get_balance()
currency = 'DOT'
amount = 100
spot_symbol = 'BTCUSDT'
cm_symbol = 'BTCUSD_PERP'
side = 'BUY'

# res = api.query_pm_balance('BTC')
# res = api.open(currency, amount)
# res = api.close(currency, amount)
# res = api.check_pos_balance(currency)
# res = api.query_pm_cm_account(symbol)
# res = api.margin_trade(currency, 99.1729296, 'SELL')
# res = api.spot_client.account.get_account()
# res = api.spot_client.market.get_depth(spot_symbol, 3)
# res = api.cm_client.market.get_depth(cm_symbol, 5)

res = api.query_jicha_open(cm_symbol, spot_symbol)
res = api.query_jicha_close(cm_symbol, spot_symbol)

# res = api.pm_client.setOrder.set_cm_order(symbol=symbol, side='SELL', positionSide='LONG', type='MARKET', quantity=1)

# res = api.query_pm_balance('BTC')

# res = api.margin_trade('ETH', amount=20, side='BUY')
# res = api.spot_client.trade.set_order(symbol='BNBUSDT', side='BUY', type='MARKET', quoteOrderQty=8)


print(json.dumps(res))