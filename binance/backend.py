from binance_interface.api import SPOT  # 现货
from binance_interface.api import Margin  # 杠杆
from binance_interface.api import CM  # CM
from binance_interface.api import PM  # 统一账户
from binance_interface.api import Other  # 其它
from binance_interface.app.utils import eprint
import json
import time
import math
import logging as lg

lg.basicConfig(level=lg.INFO,
               format='%(asctime)s.%(msecs)03d %(levelname)s ' +
               '%(filename)s:%(lineno)d: %(message)s',
               datefmt='%Y-%m-%d %H:%M:%S',
            #    filename='./logs/{}.log'.format(datetime.date.today().strftime('%Y%m%d'))
               )

CASH = 'USDT'

# currency eg: BTC
def get_spot_symbol(currency):
    return currency + CASH


def get_cm_perp_symbol(currency):
    return currency + 'USD_PERP'


class API():
    def __init__(self, key, secret, amount_unit=100) -> None:
        self.key = None
        self.set_key(key, secret)
        # 开仓、平仓操作 金额单位
        self.amount_unit = amount_unit

        self.cm_perp_symbols = None
        self.cm_perp_info = None
        self.query_cm_exchange_info()
    
    
    def set_key(self, key, secret) -> None:
        assert key is not None and len(key) > 0
        if key != self.key:
            self.key = key
            self.secret = secret
            self.spot_client = SPOT(key, secret)
            self.margin_client = Margin(key, secret)
            self.cm_client = CM(key, secret)
            self.pm_client = PM(key, secret)
            self.other_client = Other(key, secret)
    
    
    # symbol such as BTCUSDT
    def query_spot_price(self, symbol):
        res = self.spot_client.market.get_ticker_price(symbol)
        data = check_resp(res)
        return float(data['price'])
    
    
    def query_wallet_balance(self):
        res = self.other_client.wallet.get_asset_wallet_balance()
        data = check_resp(res)
        total_balance = 0
        funding_balance = 0
        union_balance = 0
        price = self.query_spot_price('BTCUSDT')
        for d in data:
            # BTC计价，不知道为什么
            balance = price * float(d['balance'])
            lg.info('%s:%s', d['walletName'], balance)
            if 'Funding' == d['walletName']:
                funding_balance = balance
            elif '(PM)' in d['walletName']:
                union_balance += balance
            total_balance += balance
        return total_balance, funding_balance, union_balance
    
    
    def query_pm_account_asset(self):
        # asset为空时查询所有币种余额，相当于持仓
        res = self.pm_client.account.get_balance()
        data = check_resp(res)
        total = 0
        # 持仓量大于0的币种序列
        valid_assets = []
        for d in data:
            amount = float(d['totalWalletBalance'])
            if amount <= 1e-6:
                continue
            valid_assets.append(d)
            if CASH == d['asset']:
                total += amount
            else:
                price = self.query_spot_price(get_spot_symbol(d['asset']))
                total += price * amount
        return total, valid_assets
    
    
    # 查询某个币在所有账户的中的余额
    def query_pm_balance(self, currency):
        # asset为空时查询所有币种余额，相当于持仓
        res = self.pm_client.account.get_balance(currency)
        data = check_resp(res)
        # {'asset': 'ETH', 'totalWalletBalance': '0.05231128', 'crossMarginAsset': '0.0027972', 'crossMarginBorrowed': '0.0', 'crossMarginFree': '0.0027972', 'crossMarginInterest': '0.0', 'crossMarginLocked': '0.0', 'umWalletBalance': '0.0', 'umUnrealizedPNL': '0.0', 'cmWalletBalance': '0.04951408', 'cmUnrealizedPNL': '0.00005854', 'updateTime': 1719907200232, 'negativeBalance': '0.0'}
        return data


    # 购买BNB，充当手续费
    # amount: 交易金额
    def spot_trade(self, symbol='BNBUSDT', amount=0, side='BUY'):
        # 获取最新价格
        if amount <= 0:
            return
        price = self.query_spot_price(symbol)
        quantity = "{:.6f}".format(amount / price)
        lg.info('---买入现货%s, 金额:%s, 数量: %s, 币价:%s', symbol, amount, quantity, price)
        res = self.spot_client.trade.set_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
        data = check_resp(res)
        assert len(data['symbol']) > 0 and data['orderId'] > 0
    

    def get_cm_exchange_info(self):
        self.query_cm_exchange_info()
        # self.cm_perp_symbols: BTCUSD_PERP,ETHUSD_PERP,LINKUSD_PERP
        return self.cm_perp_symbols, self.cm_perp_info


    # 查询所有永续合约币种
    def query_cm_exchange_info(self):
        res = self.cm_client.market.get_exchangeInfo()
        data = check_resp(res)
        cm_perp_symbols = []
        cm_perp_info = {}
        for asset in data['symbols']:
            symbol = asset['symbol']
            if symbol.endswith('_PERP'):
                currency = symbol.rstrip('USD_PERP')
                cm_perp_info[currency] = {
                    'contractSize': asset['contractSize'] # 合约单价，20240701: BTC:100U,其他10U
                }
                cm_perp_symbols.append(currency)
        lg.info('所有币本位永续合约币种: %s', ','.join(cm_perp_symbols))
        self.cm_perp_info = cm_perp_info
        self.cm_perp_symbols = cm_perp_symbols
    
    
    # 统一账户合约交易
    def cm_trade(self, symbol, side, quantity):
        if not symbol.endswith('USD_PERP'):
            symbol = get_cm_perp_symbol(symbol)
        res = self.pm_client.setOrder.set_cm_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
        data = check_resp(res)
        if len(data['symbol']) > 0 and data['orderId'] > 0:
            return 0
        # error
        return 1
    
    
    # 统一账户杠杆交易
    def margin_trade(self, symbol, amount, side, quantity=None):
        # 获取最新价格
        if not symbol.endswith('USDT'):
            symbol = get_spot_symbol(symbol)
        q = quantity
        if q is None:
            price = self.query_spot_price(symbol)
            q = "{:.8f}".format(amount / price)
        res = self.pm_client.setOrder.set_margin_order(symbol=symbol, side=side, type='MARKET', quantity=q)
        data = check_resp(res)
        if len(data['symbol']) > 0 and data['orderId'] > 0:
            return 0
        # error 
        return 1
    

    def risk_check(self):
        # todo
        return True

    
    # 单次开仓
    def trade_once(self, currency, amount):
        lg.info('开仓: %s, 金额: %sU', currency, amount)
        swap_transaction_result = 0
        # retry
        for i in range(3):
            lg.info('***%s开仓%sU***, run %s/3', currency, amount, i+1)
            if swap_transaction_result == 0:
                cm_symbol = get_cm_perp_symbol(currency)
                cm_amount = amount / self.cm_perp_info[cm_symbol]['contractSize']
                lg.info("***开始%s合约做空, 本次交易张数为%s", cm_symbol, cm_amount)
                res1 = self.cm_trade(cm_symbol, 'SELL', cm_amount)
                if res1 == 0:
                    swap_transaction_result = 1
                    lg.info("***%s合约做空成功, 本次交易张数为%s", cm_symbol, cm_amount)
                    spot_symbol = get_spot_symbol(currency)
                    lg.info("***开始%s杠杆做多, 本次交易金额为%s", spot_symbol, amount)
                    res2 = self.margin_trade(spot_symbol, amount, 'BUY')
                    if res2 == 0:
                        lg.info("***%s杠杆做多成功, 本次交易金额为%s", spot_symbol, amount)
                        return 0
                    else:
                        lg.info("***%s杠杆做多失败, 本次交易金额为%s", spot_symbol, amount)
                else:
                    lg.info("***%s合约做失败, 本次交易张数为%s", cm_symbol, cm_amount)
            else:
                print("%s合约交易成功, 但是杠杆交易没成功, 重试杠杆交易", cm_symbol)
                spot_symbol = get_spot_symbol(currency)
                lg.info("***开始%s杠杆做多, 本次交易金额为%s", spot_symbol, amount)
                res2 = self.margin_trade(spot_symbol, amount, 'BUY')
                if res2 == 0:
                    lg.info("***%s杠杆做多成功, 本次交易金额为%s", spot_symbol, amount)
                    return 0
                else:
                    lg.info("***%s杠杆做多失败, 本次交易金额为%s", spot_symbol, amount)
        return 1
    
    
    # 单次平仓
    def clear_once(self, currency, amount):
        lg.info('平仓: %s, 金额: %sU', currency, amount)
        swap_transaction_result = 0
        # retry
        cm_symbol = get_cm_perp_symbol(currency)
        spot_symbol = get_spot_symbol(currency)
        for i in range(3):
            lg.info('***%s平仓%sU***, run %s/3', currency, amount, i+1)
            if swap_transaction_result == 0:
                cm_amount = amount / self.cm_perp_info[cm_symbol]['contractSize']
                lg.info("***开始%s合约平仓, 本次交易张数为%s", cm_symbol, cm_amount)
                res1 = self.cm_trade(cm_symbol, 'BUY', cm_amount)
                if res1 == 0:
                    swap_transaction_result = 1
                    lg.info("***%s合约平仓成功, 本次交易张数为%s", cm_symbol, cm_amount)
                    ava_bal = self.query_pm_balance(currency)
                    amount_margin = ava_bal if ava_bal < amount else amount
                    lg.info("***开始%s杠杆平仓, 本次交易金额为%s", spot_symbol, amount_margin)
                    res2 = self.margin_trade(spot_symbol, amount_margin, 'SELL')
                    if res2 == 0:
                        lg.info("***%s杠杆平仓成功, 本次交易金额为%s", spot_symbol, amount_margin)
                        return 0
                    else:
                        lg.error("***%s杠杆平仓失败, 本次交易金额为%s", spot_symbol, amount_margin)
                else:
                    lg.error("***%s合约平仓失败, 本次交易张数为%s", cm_symbol, cm_amount)
            else:
                print("%s合约平仓成功, 但是杠杆平仓没成功, 重试杠杆平仓", cm_symbol)
                spot_symbol = get_spot_symbol(currency)
                ava_bal = self.query_pm_balance(currency)
                amount_margin = ava_bal if ava_bal < amount else amount
                lg.info("***开始%s杠杆平仓, 本次交易金额为%s", spot_symbol, amount_margin)
                res2 = self.margin_trade(spot_symbol, amount_margin, 'SELL')
                if res2 == 0:
                    lg.info("***%s杠杆平仓成功, 本次交易金额为%s", spot_symbol, amount_margin)
                    return 0
                else:
                    lg.error("***%s杠杆平仓失败, 本次交易金额为%s", spot_symbol, amount_margin)
        return 1


    def check_pos_balance(self):
        # todo
        return True
    
    
    # 开仓流程
    def open(self, currency, amount):
        cnt = math.floor(amount / self.amount_unit)
        lg.info('%s开仓%sU,将分%s次开仓, 每次%sU,不足部分不开仓', currency, amount, cnt, self.amount_unit)
        self.spot_trade(symbol='BNBUSDT', amount=0.00075*amount)

        for i in range(cnt):
            lg.info('开仓 第%s/%s轮', i+1, cnt)
            res = self.trade_once(currency, self.amount_unit)
            if res > 0:
                lg.error('****开仓有异常, 请查看日志****')
                break
            if not self.check_pos_balance():
                lg.error('仓位不平衡, 请排查')
                break
            if (i+1) % 10 == 0:
                # 避免限频
                time.sleep(3)
    
    # 平仓流程
    # amount为具体金额时平仓这么多钱，amount为None时清仓
    # symbol: BTC
    def close(self, currency, amount=None):
        balance_min = 200
        lg.info('----------平仓: %s, 不足%sU部分会一次清仓----------', currency, balance_min)
        symbol_balance = self.query_pm_balance(currency)
        balance = float(symbol_balance['crossMarginAsset'])
        if balance <= balance_min:
            lg.info('---余额%s不足%sU, 执行清仓', balance_min, balance)
            self.clear_once(currency, balance_min)
            lg.info('---清仓成功')
            return 0

        if amount is None or balance < amount:
            lg.info('---余额[%s]小于输入金额[%s]或者未输入平仓金额', balance, amount)
            amount = balance
        loop = math.floor(amount / self.amount_unit)
        for i in range(loop):
            self.clear_once(currency, self.amount_unit)
            if not self.risk_check():
                lg.warning('----------交易异常,请排查----------')
                return 1
        
        # 再次check余额
        symbol_balance = self.query_pm_balance(currency)
        balance = float(symbol_balance['crossMarginAsset'])
        if balance <= balance_min:
            lg.info('---余额%s不足%sU或者点了清仓, 直接清仓', balance_min, balance)
            self.clear_once(currency, balance)
        lg.info('---清仓成功')
        return 0


    def transfer(self, type, symbol, amount):
        res = self.other_client.wallet.set_asset_transfer(type, symbol, amount)
        check_resp(res)


def check_resp(res):
    # lg.info('---res: %s',  json.dumps(res))
    # eprint(res)
    if res['code'] != 200:
        lg.error('request error, code: %s, msg: %s', res['code'], res['msg'])
        raise Exception("request error")
    return res['data']