# from binance.spot import Spot
from binance_interface.api import SPOT  # 现货
from binance_interface.api import Margin  # 杠杆
from binance_interface.api import CM  # CM
from binance_interface.api import PM  # 统一账户
from binance_interface.api import Other  # 其它
from binance_interface.app.utils import eprint
import pandas as pd
import datetime
import requests
import logging as lg

lg.basicConfig(level=lg.INFO,
               format='%(asctime)s.%(msecs)03d %(levelname)s ' +
               '%(filename)s:%(lineno)d: %(message)s',
               datefmt='%Y-%m-%d %H:%M:%S',
            #    filename='./logs/{}.log'.format(datetime.date.today().strftime('%Y%m%d'))
               )

class API():
    def __init__(self, key, secret, amout_unit=100) -> None:
        self.key = key
        self.secret = secret
        self.spot_client = SPOT(key, secret)
        self.margin_client = Margin(key, secret)
        self.cm_client = CM(key, secret)
        self.pm_client = PM(key, secret)
        self.other_client = Other(key, secret)

        # 开仓、平仓操作 金额单位
        self.amout_unit = amout_unit
    

    def query_spot_price(self, symbol):
        res = self.spot_client.market.get_ticker_price(symbol)
        data = check_resp(res)
        price = data[0]['price']
        return price
    
    
    def query_wallet_balance(self):
        res = self.other_client.wallet.get_asset_wallet_balance()
        data = check_resp(res)
        total_balance = -1
        funding_balance = -1
        for d in data:
            if 'Funding' == d['walletName']:
                funding_balance = d['balance']
            total_balance += d['balance']
        return total_balance, funding_balance
    
    
    # def query_funding_balance(self):
    #     res = self.other_client.wallet.set_asset_get_funding_asset()
    #     data = check_resp(res)
    #     for d in data:
    #         if 'USDT' == d['asset']:
    #             return d['free']
    #     return -1
    
    
    def query_pm_balance(self):
        res = self.pm_client.account.get_balance()
        data = check_resp(res)
        for d in data:
            if 'USDT' == d['asset']:
                return d['totalWalletBalance']
        return -1


    # 购买BNB，充当手续费
    # amount: 交易金额
    def spot_trade(self, symbol='BNBUSDT', amount=0, side='BUY'):
        # 获取最新价格
        if amount <= 0:
            return
        price = self.query_spot_price(symbol)
        quantity = "{:.8f}".format(amount / price)
        res = self.spot_client.trade.set_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
        data = check_resp(res)
        assert len(data['symbol']) > 0 and data['orderId'] > 0
    

    # 查询所有永续合约币种
    def query_cm_perp(self):
        res = self.cm_client.market.get_exchangeInfo()
        data = check_resp(res)
        cm_perp_symbols = []
        for asset in data['symbols']:
            symbol = asset['symbol']
            if symbol.endswith('_PERP'):
                cm_perp_symbols.append(symbol)
        lg.info('all perp symbols: %s', ','.join(cm_perp_symbols))
        return cm_perp_symbols
    
    
    # 查询永续合约币种余额
    def query_margin_balance(self, symbol=None):
        # todo
        res = self.margin_client.accountTrade.get_margin_allAssets()
        lg.info('--query_margin_balance: %s', res)
        data = check_resp(res)
        symbol_balance = {}
        for asset in data:
            symbol_balance[asset['assetName']] = asset['free']
        if symbol is not None and symbol in symbol_balance:
            return symbol_balance['symbol']
        return symbol_balance


    # 统一账户合约交易
    def cm_trade(self, symbol, amount, side='BUY'):
        # 获取最新价格
        res = self.cm_client.market.get_ticker_price(symbol)
        data = check_resp(res)
        price = data[0]['price']
        quantity = "{:.8f}".format(amount / price)
        res = self.pm_client.setOrder.set_cm_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
        data = check_resp(res)
        assert len(data['symbol']) > 0 and data['orderId'] > 0
    
    
    # 统一账户杠杆交易
    def margin_trade(self, symbol, amount, side='BUY'):
        # 获取最新价格
        price = self.query_spot_price(symbol)
        quantity = "{:.8f}".format(amount / price)
        res = self.pm_client.setOrder.set_margin_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
        data = check_resp(res)
        assert len(data['symbol']) > 0 and data['orderId'] > 0
    

    def risk_check(self):
        # todo
        return True

    
    # 开仓流程
    def open(self, symbol, amount):
        lg.info('开仓: %s, 总金额: %sU, 不足%sU部分不会交易', symbol, amount, self.amout_unit)
        for i in range(int(amount / self.amout_unit)):
            lg.info('永续合约开始第%s轮卖出', i)
            self.cm_trade(symbol, self.amout_unit, 'SELL')
            lg.info('杠杆交易开始第%s轮买入', i)
            self.margin_trade(symbol, self.amout_unit, 'BUY')
            if not self.risk_check():
                lg.warning('----------交易异常,请排查----------')
                break
    
    
    # 平仓流程
    # amount为具体金额时平仓这么多钱，amount为None时清仓
    def close(self, symbol, amount=None):
        balance_min = 200
        lg.info('----------平仓: %s, 不足%sU部分会一次清仓----------', symbol, balance_min)
        balance = self.query_margin_balance(symbol)
        if balance <= balance_min or amount is None:
            lg.info('---余额%s不足%sU或者点了清仓, 直接清仓', balance_min, balance)
            self.cm_trade(symbol, balance, 'BUY')
            self.margin_trade(symbol, balance, 'SELL')
            lg.info('---清仓成功')
            return

        if balance < amount:
            lg.info('---余额[%s]小于输入金额[%s]，按清仓处理', balance, amount)
            amount = balance
        for i in range(int(amount / self.amout_unit)):
            lg.info('永续合约开始第%s轮平仓', i)
            self.cm_trade(symbol, self.amout_unit, 'BUY')
            lg.info('杠杆交易开始第%s轮卖出', i)
            self.margin_trade(symbol, self.amout_unit, 'SELL')
            if not self.risk_check():
                lg.warning('----------交易异常,请排查----------')
                break
            remaining = amount - (i+1) * self.amout_unit
            if remaining <= balance_min:
                lg.info('---余额%s不足%sU, 直接清仓', remaining, balance_min)
                self.cm_trade(symbol, remaining, 'BUY')
                self.margin_trade(symbol, remaining, 'SELL')
                break
        lg.info('---清仓成功')

    
    def transfer(self, symbol, amount, type):
        res = self.other_client.wallet.set_asset_transfer(type, symbol, amount)
        check_resp(res)


def check_resp(res):
    if res['code'] != 200:
        lg.error('request error, code: %s, msg: %s', res['code'], res['msg'])
        raise Exception("request error")
    return res['data']