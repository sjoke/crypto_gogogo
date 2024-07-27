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
import pandas as pd
from IPython.display import display


lg.basicConfig(level=lg.INFO,
               format='%(asctime)s.%(msecs)03d %(levelname)s ' +
               '%(filename)s:%(lineno)d: %(message)s',
               datefmt='%Y-%m-%d %H:%M:%S',
            #    filename='./logs/{}.log'.format(datetime.date.today().strftime('%Y%m%d'))
               )

CASH = 'USDT'
MIN_POSITION = 1e-6

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
        bal_dict = {}
        total_balance = 0
        union_balance = 0
        price = self.query_spot_price('BTCUSDT')
        for d in data:
            # BTC计价，不知道为什么
            balance = price * float(d['balance'])
            bal_dict[d['walletName']] = balance
            total_balance += balance
            if '(PM)' in d['walletName']:
                union_balance += balance
        bal_dict['Total'] = total_balance
        bal_dict['Union'] = union_balance
        print('***账户总资产: {:.2f}U, 现货账户总资产: {:.2f}U, 统一账户总资产: {:.2f}U, 资金账户总资产:{:.2f}' \
            .format(bal_dict['Total'], bal_dict['Spot'], bal_dict['Union'], bal_dict['Funding']))
        return bal_dict
    
    # 查询现货账户持仓
    def query_spot_position(self):
        res = self.spot_client.account.get_account()
        data = check_resp(res)
        valid_assets = []
        for d in data['balances']:
            currency = d['asset']
            free = float(d['free'])
            if free < MIN_POSITION:
                continue
            valid_asset = {
                'account_type': '现货账户',
                'currency': currency,
                'balance': free,
            }
            if currency != CASH:
                valid_asset['price'] = self.query_spot_price(get_spot_symbol(currency))
                valid_asset['value'] = valid_asset['price'] * free
            else:
                valid_asset['price'] = 1
                valid_asset['value'] = free
            if valid_asset['value'] > 1:
                valid_assets.append(valid_asset)
        valid_assets.sort(key=lambda x: -x['value'])
        return valid_assets
    
    
    # 查询资金账户持仓
    def query_funding_position(self):
        res = self.other_client.wallet.set_asset_get_funding_asset()
        data = check_resp(res)
        valid_assets = []
        for d in data:
            currency = d['asset']
            free = float(d['free'])
            if free < MIN_POSITION:
                continue
            valid_asset = {
                'account_type': '资金账户',
                'currency': currency,
                'balance': free,
            }
            if currency != CASH:
                valid_asset['price'] = self.query_spot_price(get_spot_symbol(currency))
                valid_asset['value'] = valid_asset['price'] * free
            else:
                valid_asset['price'] = 1
                valid_asset['value'] = free
            if valid_asset['value'] > 1:
                valid_assets.append(valid_asset)
        valid_assets.sort(key=lambda x: -x['value'])
        return valid_assets
    

    # 查询统一账户净资产
    def query_pm_position(self):
        # asset为空时查询所有币种余额，相当于持仓
        res = self.pm_client.account.get_balance()
        data = check_resp(res)
        # 持仓量大于0的币种序列
        valid_assets = []
        for d in data:
            currency = d['asset']
            free = float(d['totalWalletBalance'])
            if abs(free) < MIN_POSITION:
                continue
            valid_asset = {
                'account_type': '统一账户',
                'currency': d['asset'],
                'balance': free
            }
            if currency != CASH:
                valid_asset['price'] = self.query_spot_price(get_spot_symbol(currency))
                valid_asset['value'] = valid_asset['price'] * free
            else:
                valid_asset['price'] = 1
                valid_asset['value'] = free
            if valid_asset['value'] > 1:
                valid_assets.append(valid_asset)
        valid_assets.sort(key=lambda x: -x['value'])
        return valid_assets


    def get_all_position(self):
        positions = []
        positions.extend(self.query_spot_position())
        positions.extend(self.query_funding_position())
        positions.extend(self.query_pm_position())
        df = pd.DataFrame(positions)

        pos2 = self.check_pm_position()
        df2 = pd.DataFrame(pos2)
        with pd.option_context('display.max_rows', None,
                       'display.max_columns', None,
                       'display.precision', 2,
                       ):
            print("-----账户持仓情况--------------")
            display(df)
            print("-----统一账户合约和净资产情况-----")
            display(df2)

    
    # 查询净资产和合约仓位是否平衡
    # 净资产数量*价格 和合约张数*合约价格 比较
    def check_pm_position(self):
        # asset为空时查询所有币种余额，相当于查询持仓
        res = self.pm_client.account.get_balance()
        data = check_resp(res)
        # 持仓量大于0的币种序列
        valid_assets = []
        for d in data:
            if abs(float(d['totalWalletBalance'])) < MIN_POSITION:
                continue
            currency = d['asset']
            if CASH != d['asset']:
                # {
                #     'currency': currency,
                #     'contract_size': contract_size,
                #     'amt': amt,
                #     '合约单价*张数': contract_size * amt,
                #     'balance': balance,
                #     'price': price,
                #     '净资产价值/U': balance * price,
                # }
                pos_d = self.check_pos_balance(currency, only_query=True)
                if abs(pos_d['amt']) < 1 and pos_d['净资产价值/U'] < 1:
                    continue
                valid_assets.append(pos_d)
        valid_assets.sort(key=lambda x: -x['净资产价值/U'])
        return valid_assets
    

    # 查询账户资产及持仓
    def query_account_asset(self):
        # 查询各种账户总资产
        self.query_wallet_balance()
        # 查询统一账户持仓
        self.get_all_position()
    
    
    # 查询某个币在统一账户的中的余额
    def query_pm_balance(self, currency):
        # asset为空时查询所有币种余额，相当于持仓
        res = self.pm_client.account.get_balance(currency)
        data = check_resp(res)
        # {'asset': 'ETH', 'totalWalletBalance': '0.05231128', 'crossMarginAsset': '0.0027972', 'crossMarginBorrowed': '0.0', 'crossMarginFree': '0.0027972', 'crossMarginInterest': '0.0', 'crossMarginLocked': '0.0', 'umWalletBalance': '0.0', 'umUnrealizedPNL': '0.0', 'cmWalletBalance': '0.04951408', 'cmUnrealizedPNL': '0.00005854', 'updateTime': 1719907200232, 'negativeBalance': '0.0'}
        return data
    

    # BOTH持仓模式下,一个币种有LONG和SHORT两种仓位
    def query_pm_cm_account(self):
        res = self.pm_client.account.get_cm_account()
        data = check_resp(res)
        # 持仓>0的币种
        valid_positons = []
        for position in data['positions']:
            amt = float(position['positionAmt'])
            if abs(amt) <= 0.001:
                # 过滤0持仓币种
                continue
            valid_positons.append(position)
        return valid_positons


    # 查询合约净持仓 = LONG持仓+SHORT持仓
    def query_pm_cm_position_amt(self, symbol):
        positions = self.query_pm_cm_account()
        amt = 0
        for pos in positions:
            if pos['symbol'] == symbol:
                amt += int(pos['positionAmt'])
        return amt
                


    # 购买BNB，充当手续费
    # quoteOrderQty: 交易金额,多少U
    def spot_trade(self, symbol='BNBUSDT', quoteOrderQty=0, side='BUY'):
        # 获取最新价格
        lg.info('---买入现货%s, 金额:%sU', symbol, quoteOrderQty)
        res = self.spot_client.trade.set_order(symbol=symbol, side=side, type='MARKET', quoteOrderQty=quoteOrderQty)
        data = check_resp(res)
    

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
                cm_perp_info[symbol] = {
                    'contractSize': asset['contractSize'] # 合约单价，20240701: BTC:100U,其他10U
                }
                cm_perp_symbols.append(symbol)
        lg.info('所有币本位永续合约币种: %s', ','.join(cm_perp_symbols))
        self.cm_perp_info = cm_perp_info
        self.cm_perp_symbols = cm_perp_symbols
    
    
    # 统一账户合约交易
    # quantity: 合约张数
    # 买long是做多，卖long是平多
    # 买short应该是做空，卖short是平空  --使用此逻辑
    # 20240713更正: both持仓模式下, 做空/开仓 sell short, 做多/平仓 buy short
    def cm_trade(self, symbol, side, quantity):
        if abs(quantity) < 1:
            lg.error("合约下单张数必须大于1, 当前是%s", quantity)
            return 2
        if not symbol.endswith('USD_PERP'):
            symbol = get_cm_perp_symbol(symbol)
        lg.info("%s %s SHORT %s张", symbol, side, quantity)
        res = self.pm_client.setOrder.set_cm_order(symbol=symbol, side=side, positionSide='SHORT', type='MARKET', quantity=quantity)
        data = check_resp(res)
        if len(data['symbol']) > 0 and data['orderId'] > 0:
            return 0
        # error
        return 1
    
    # 界面操作
    def cm_trade_op(self, currency, side, quantity=0, amount=0):
        lg.info("%s %s SHORT %s张, %sU", currency, side, quantity, amount)
        if quantity == 0 and amount > 0:
            cm_symbol = get_cm_perp_symbol(currency)
            quantity = int(amount / self.cm_perp_info[cm_symbol]['contractSize'])
        return self.cm_trade(currency, side, quantity)
    
    
    # 统一账户杠杆交易
    # amount代表多少U, quantity代表币计量
    def margin_trade(self, symbol, amount=0, side='BUY', quantity=0):
        # 获取最新价格
        if not symbol.endswith('USDT'):
            symbol = get_spot_symbol(symbol)
        if amount > 0:
            lg.info('margin_trade: %s, %s, %sU', symbol, side, amount)
            res = self.pm_client.setOrder.set_margin_order(symbol=symbol, side=side, type='MARKET', quoteOrderQty=amount)
        elif quantity > 0:
            lg.info('margin_trade: %s, %s, %s个', symbol, side, quantity)
            res = self.pm_client.setOrder.set_margin_order(symbol=symbol, side=side, type='MARKET', quantity=quantity)
        data = check_resp(res)
        if len(data['symbol']) > 0 and data['orderId'] > 0:
            return 0
        return 1

    
    # 单次开仓
    # amount代表多少U, eg BTC, 100
    def open_once(self, currency, amount):
        lg.info('开仓: %s, 金额: %sU', currency, amount)
        swap_transaction_result = 0
        # retry
        for i in range(3):
            lg.info('***%s开仓%sU***, run %s/retry 3', currency, amount, i+1)
            if swap_transaction_result == 0:
                cm_symbol = get_cm_perp_symbol(currency)
                contract_amount = int(amount / self.cm_perp_info[cm_symbol]['contractSize'])
                lg.info("***开始%s合约做空, 本次交易张数为%s", cm_symbol, contract_amount)
                res1 = self.cm_trade(cm_symbol, 'SELL', contract_amount)
                if res1 == 0:
                    swap_transaction_result = 1
                    lg.info("***%s合约做空成功, 本次交易张数为%s", cm_symbol, contract_amount)
                    spot_symbol = get_spot_symbol(currency)
                    lg.info("***开始%s杠杆做多, 本次交易金额为%s", spot_symbol, amount)
                    res2 = self.margin_trade(spot_symbol, amount, 'BUY')
                    if res2 == 0:
                        lg.info("***%s杠杆做多成功, 本次交易金额为%s", spot_symbol, amount)
                        return 0
                    else:
                        lg.info("***%s杠杆做多失败, 本次交易金额为%s", spot_symbol, amount)
                else:
                    lg.info("***%s合约做失败, 本次交易张数为%s", cm_symbol, contract_amount)
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
        amount = float("{:.4f}".format(amount))
        lg.info('平仓: %s, 金额: %sU', currency, amount)
        swap_transaction_result = 0
        cm_symbol = get_cm_perp_symbol(currency)
        spot_symbol = get_spot_symbol(currency)
        # retry
        for i in range(3):
            lg.info('***%s平仓%sU***, run %s/3', currency, amount, i+1)
            if swap_transaction_result == 0:
                contract_amount = round(amount / self.cm_perp_info[cm_symbol]['contractSize'])
                lg.info("***开始%s合约平仓, 本次交易张数为%s", cm_symbol, contract_amount)
                res1 = self.cm_trade(cm_symbol, 'BUY', contract_amount)
                if res1 == 0:
                    swap_transaction_result = 1
                    lg.info("***%s合约平仓成功, 本次交易张数为%s", cm_symbol, contract_amount)
                    lg.info("***开始%s杠杆平仓, 本次交易金额为%s", spot_symbol, amount)
                    res2 = self.margin_trade(spot_symbol, amount, 'SELL')
                    if res2 == 0:
                        lg.info("***%s杠杆平仓成功, 本次交易金额为%s", spot_symbol, amount)
                        return 0
                    else:
                        lg.error("***%s杠杆平仓失败, 本次交易金额为%s", spot_symbol, amount)
                else:
                    lg.error("***%s合约平仓失败, 本次交易张数为%s", cm_symbol, contract_amount)
            else:
                print("%s合约平仓成功, 但是杠杆平仓没成功, 重试杠杆平仓", cm_symbol)
                lg.info("***开始%s杠杆平仓, 本次交易金额为%s", spot_symbol, amount)
                res2 = self.margin_trade(spot_symbol, amount, 'SELL')
                if res2 == 0:
                    lg.info("***%s杠杆平仓成功, 本次交易金额为%s", spot_symbol, amount)
                    return 0
                else:
                    lg.error("***%s杠杆平仓失败, 本次交易金额为%s", spot_symbol, amount)
        return 1


    def check_pos_balance(self, currency, only_query=False):
        cm_symbol = get_cm_perp_symbol(currency)
        spot_symbol = get_spot_symbol(currency)
        # 合约每张单价
        contract_size = self.cm_perp_info[cm_symbol]['contractSize']
        # 持有张数
        amt = self.query_pm_cm_position_amt(cm_symbol)
        money1 = abs(contract_size * amt)
        # lg.info('%s, CM合约张数: %s, 合约单价: %.1f, 持仓金额: %.8f', currency, amt, contract_size, money1)

        # 统一账户净资产
        balance = float(self.query_pm_balance(currency)['totalWalletBalance'])
        # 现货价格
        price = self.query_spot_price(spot_symbol)
        money2 = abs(balance * price)
        # lg.info('%s, 统一账户净资产: %.8f, 市场价: %.8f, 持仓金额: %.8f', currency, balance, price, money2)

        if only_query:
            return {
                'currency': currency,
                'contract_size': contract_size,
                'amt': amt,
                '合约单价*张数': contract_size * amt,
                'balance': balance,
                'price': price,
                '净资产价值/U': balance * price,
            }
        # 要求二者持仓相反,且持仓绝对金额想近才认为平衡
        if amt * balance > 0:
            lg.error("----合约持仓方向与杠杆持仓方向一致，请排查----")
            return False
        if abs(money1 - money2) <= 3:
            return True
        base = money1 if money1 > money2 else money2
        if (abs(money1 - money2) / base) <= 0.02:
            return True
        return False
    
    
    # 开仓流程
    # amount为U
    # 合约sell short， 杠杆buy
    def open(self, currency, amount):
        cnt = math.floor(amount / self.amount_unit)
        lg.info('%s开仓%sU,将分%s次开仓,每次%sU,不足部分不开仓', currency, amount, cnt, self.amount_unit)
        if 0.00075*amount > 5:
            lg.info('----买入BNB, %s U----', 0.00075*amount)
            self.margin_trade(symbol='BNBUSDT', amount=0.00075*amount)

        for i in range(cnt):
            lg.info('开仓%sU 第%s/%s轮', self.amount_unit, i+1, cnt)
            res = self.open_once(currency, self.amount_unit)
            if res > 0:
                lg.error('****开仓有异常, 请查看日志****')
                break
            if not self.check_pos_balance(currency):
                lg.error('仓位不平衡, 请排查')
                break
            if (i+1) % 5 == 0:
                # 避免限频
                time.sleep(3)
    
    # 平仓流程
    # currency: BTC
    # amount为具体金额时平仓这么多钱，amount为None时清仓
    def close(self, currency, amount=None):
        if not self.check_pos_balance(currency):
            lg.error("仓位不平衡，请先排查")
            return 2
        balance_min = 200
        lg.info('----------平仓: %s, 不足%sU部分会一次清仓----------', currency, balance_min)
        crossMarginFree = float(self.query_pm_balance(currency)['crossMarginFree'])
        spot_symbol = get_spot_symbol(currency)
        price = self.query_spot_price(spot_symbol)
        balance = abs(crossMarginFree * price)
        
        if balance <= balance_min:
            lg.info('---余额%s不足%sU, 执行清仓', balance, balance_min)
            self.clear_once(currency, balance)
            lg.info('---清仓成功')
            return 0

        if amount is None or balance < amount:
            lg.info('---余额[%s]小于输入金额[%s]或者未输入平仓金额,按清仓处理', balance, amount)
            amount = balance
        loop = math.floor(amount / self.amount_unit)
        for i in range(loop):
            lg.info('平仓%sU 第%s/%s轮', self.amount_unit, i+1, loop)
            self.clear_once(currency, self.amount_unit)
            if not self.check_pos_balance(currency):
                lg.error('----------交易异常,请排查----------')
                return 1
        
        # 再次check余额
        crossMarginFree = float(self.query_pm_balance(currency)['crossMarginFree'])
        spot_symbol = get_spot_symbol(currency)
        price = self.query_spot_price(spot_symbol)
        balance = abs(crossMarginFree * price)
        if balance <= balance_min:
            lg.info('---余额%s不足%sU或者点了清仓, 直接清仓', balance_min, balance)
            self.clear_once(currency, balance)
        lg.info('---清仓成功')
        return 0


    def transfer(self, type, symbol, amount):
        res = self.other_client.wallet.set_asset_transfer(type, symbol, amount)
        check_resp(res)
        lg.info('转账成功!')


def check_resp(res):
    # lg.info('---res: %s',  json.dumps(res))
    # eprint(res)
    if res['code'] != 200:
        s = 'request error, code: %s, msg: %s' %(res['code'], res['msg'])
        raise Exception(s)
    return res['data']