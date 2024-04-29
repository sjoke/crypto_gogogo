# ----*coding = utf-8*----

from okx_api import Market
from okx_api import Public
from okx_api import Trade
from okx_api import Account
import time
import datetime
from tqdm.notebook import tqdm


CASH = 'USDT'

# only for test
KEY = '8d0cffcb-6765-4566-bd59-72a4b6b26180'
SECRET = 'DB0C16E298D8AE45A57C8B20168391F4'
PASSPHRASE = '111@Cmfchina.com'
FLAG = '0' #0实仓，1模拟交易

RISK = {'low': 0, 'mid': 1, 'high': 2}
TRADE_BASE_AMOUNT = 20 #每笔交易金额，当前是1000u
EFFECTIVE_MARGIN_RATIO_ERR = 0.3   #告警保证金率
EFFECTIVE_MARGIN_RATIO_LIMIT = 0.4   #最低保证金率
CLEARANCE_CONDITION = 0.0005
USDT_EQ_LIMIT = 100

public = Public(flag=FLAG)
market = Market(flag=FLAG)

global_do_deordering = 0           #风控减仓中


def log(func):
    def wrapper(*args, **kwargs):
        print(f"Calling function {func.__name__} with args={args} and kwargs={kwargs}")
        result = func(*args, **kwargs)
        # print(f"Function {func.__name__} returned {result}")
        # print("请求中, 等待返回结果......")
        return result
    return wrapper

def getCcyStr(spotOrSwap):
    tmp = spotOrSwap.split('-')
    return tmp[0]

def getSpotStr(ccy):
    return ccy + '-' + CASH

def getSwapStr(ccy):
    return ccy + '-' + CASH + '-SWAP'

def getAllSwap():
    '''
    获取所有的永续合约交易对
    '''

    swaps = []

    ret = market.get_tickers(instType='SWAP')
    for i in ret['data']:
        tmp = i['instId'].split('-')
        if tmp[1] == CASH:
            swaps.append(i['instId'])
        
    return swaps

def getCcyDiscountRates(ccy):
    '''
    获取单个币种的折扣率
    '''

    result = {}

    data = public.get_discount_rate_interest_free_quota(ccy=ccy)
    code = data['code']
    data = data['data']

    discountInfo = data[0]['discountInfo']

    count = 0

    amts = []

    for j in discountInfo:
        discountRate = float(j['discountRate'])
        minAmt = float(j['minAmt'])
        if len(j['maxAmt']):
            maxAmt = float(j['maxAmt'])
        else:
            maxAmt = float('inf')
        
        pri = ccy + "在区间" + j['minAmt'] + "~" + j['maxAmt'] + "之间的折扣率是" + j['discountRate']
        print("|{:<83}|".format(pri))
        count = count + 1
        amts.append({'discountRate': discountRate, 'minAmt': minAmt, 'maxAmt': maxAmt})
        if count == 2:
            break

    result['amt'] = amts

    return result

def getRecent10FundingRates(swaps):
    '''
    获取永续合约交易对前10次的资金费率
    '''

    result = {}
    interval = 8 * 3600 * 1000 #费率每8小时更新一次
    cur = int(time.time()) * 1000
    cur = int(cur / interval) * interval

    for i in tqdm(swaps, total=len(swaps)):
        fundingRates = []
        result[i] = {}

        ret = public.get_funding_rate_history(instId=i, after=(cur+1), limit=10) #区间为[start, after)
        for j in ret['data']:
            fundingRates.append(float(j['fundingRate']))
            if int(j['fundingTime']) == cur:
                result[i]['cur'] = float(j['fundingRate'])

        result[i]['history'] = fundingRates
        if len(fundingRates) == 0:
            result[i]['avg'] = 0
        else:
            result[i]['avg'] = sum(fundingRates) / len(fundingRates)

    tmp = sorted(result.items(), key=lambda data: data[1]['avg'], reverse=True)
    result = {}
    for i in tmp:
        key = i[0]
        value = i[1]
        result[key] = value

    return result

def showRecent10FundingRates(fundingRates):
    '''
    按照从大到小的顺序显示所有合约交易对的资金费率
    '''

    j = 0

    print("-----------------------------------------------------------------------------------------------")
    print("|{:^20} {:^20} {:^20} {:^15} |".format('合约对', '平均值', '最新值', '24小时成交额'))#, 'HISTORY'))
    print("-----------------------------------------------------------------------------------------------")
    for i in fundingRates.keys():
        #result = market.get_candles(instId=i, bar='1D')
        #print(result)
        
        ccy = getCcyStr(i)

        spot = ccy + '-USDT'
        
        ret = market.get_ticker(instId=spot)
        
        volCcy24h = float(ret['data'][0]['volCcy24h'])

        print("|{:^20} {:^30} {:^20} {:^20}|".format(i, fundingRates[i]['avg'], fundingRates[i]['cur'], volCcy24h))
        
        discountrate = getCcyDiscountRates(ccy)
        print("-----------------------------------------------------------------------------------------------")
        j = j + 1
        if j == 10:
            return
        #print(fundingRates[i]['history'])

@log
def getRecent10FundingRatesMax():

    #获取所有合约最近10次费率，并按照平均费率从大到小排列
    swaps = getAllSwap()

    #获取满足条件的前十个交易对
    fundingRates = getRecent10FundingRates(swaps)

    showRecent10FundingRates(fundingRates)

@log
def getCurrentAccountFundingRatesFlow(key, secret, passphrase, flag):
    '''
    获取当前账户当天的资金费率
    '''
    account = Account(key=key, secret=secret, passphrase=passphrase, flag=flag)
    trade = Trade(key=key, secret=secret, passphrase=passphrase, flag=flag)

    now_time = int(time.time())
    day_time_1 = int(now_time - (now_time- time.timezone) % 86400)
    day_time_2 = day_time_1 - 86400
    day_time_3 = day_time_2 - 86400

    fundingrates1 = 0
    fundingrates2 = 0
    fundingrates3 = 0
    
    day_time_str1 = str(day_time_1) + "000"
    ret = account.get_bills_archive(type='8', begin=day_time_str1)
    for i in ret['data']:
        print(i['balChg'])
        fundingrates1 = fundingrates1 + float(i['balChg'])

    day_time_str2 = str(day_time_2) + "000"
    ret = account.get_bills_archive(type='8', begin=day_time_str2, end=day_time_str1)
    for i in ret['data']:
        fundingrates2 = fundingrates2 + float(i['balChg'])

    day_time_str3 = str(day_time_3) + "000"
    ret = account.get_bills_archive(type='8', begin=day_time_str3, end=day_time_str2)
    for i in ret['data']:
        fundingrates3 = fundingrates3 + float(i['balChg'])

    time_str1 = datetime.datetime.fromtimestamp(day_time_1).strftime("%Y-%m-%d")
    time_str2 = datetime.datetime.fromtimestamp(day_time_2).strftime("%Y-%m-%d")
    time_str3 = datetime.datetime.fromtimestamp(day_time_3).strftime("%Y-%m-%d")
    print("%s资金费率总收益为：%f" % (time_str1, fundingrates1))
    print("%s资金费率总收益为：%f" % (time_str2, fundingrates2))
    print("%s资金费率总收益为：%f" % (time_str3, fundingrates3))




def isOpenOrderTradeCondsSatisfied(fundingRate, ticker):
    '''
    判断当前币种是否满足交易条件：
    1. （现货卖1价-合约买1价）/现货卖1价≤3*F10-0.0005 （其中F10为10次历史资金费率的平均值）
    '''

    tmp = 3 * fundingRate['avg'] - 0.0005;
    if (ticker['spot_sell'] - ticker['swap_buy']) / ticker['spot_sell'] <= tmp:
        return True
    else:
        print("不满足现货卖一价%f - 合约买1价%f / 现货卖1价%f ≤ 3*F10(%f)-0.0005的条件" % (ticker['spot_sell'], ticker['swap_buy'], ticker['spot_sell'], fundingRate['avg']))
        return False

def getTicker(ccy, discountRates):
    '''
    获取币种现货卖1价和合约买1价
    '''

    #获取
    spot = ccy + '-' + CASH
    swap = spot + '-SWAP'
    
    spot_price = 0
    swap_price = 0
    result = {}
    for i in range(5):
        ret = market.get_ticker(instId=spot)
        if len(ret['data'][0]['askPx']) and len(ret['data'][0]['bidPx']):
            result['spot_buy'] = float(ret['data'][0]['askPx']) #askPx为买一价
            result['spot_sell'] = float(ret['data'][0]['bidPx']) #askPx为卖一价
            spot_price = 1
            break
        else:
            print("获取%s币币市场价格失败" % ccy)
            print(ret)

    for i in range(5):
        ret = market.get_ticker(instId=swap)
        if len(ret['data'][0]['askPx']) and len(ret['data'][0]['bidPx']):
            result['swap_buy'] = float(ret['data'][0]['askPx']) #askPx为买一价
            result['swap_sell'] = float(ret['data'][0]['bidPx']) #bidPx为卖一价
            swap_price = 1
            break
        else:
            print("获取%s合约市场价格失败" % ccy)
            print(ret)

    if swap_price == 0 or spot_price == 0:
        return result,1

    current_swap_val = result['swap_buy']

    #计算出开合约的张数 100u/当前价格 然后除以合约面值 得到合约张数
    result['swap_sz'] = 1 #int(TRADE_BASE_AMOUNT / current_swap_val / float(discountRates[ccy]['ct_val']))
    result['spot_sz'] = result['swap_sz'] * float(discountRates[ccy]['ct_val'])

    return result,0

def doOpenOrderTrade(trade, ccy, ticker):
    '''
    执行交易
    '''

    spot = getSpotStr(ccy)
    swap = getSwapStr(ccy)

    #合约交易张数
    swap_sz_str = str(ticker['swap_sz'])
    #现货交易金额
    spot_sz_str = str(ticker['spot_sz'])
    
    swap_transaction_result = 0

    for i in range(5):
        if swap_transaction_result == 0:
            swap_result = trade.set_order(instId=swap, tdMode='cross', side='sell', ordType='market', sz=swap_sz_str) #合约交易
            if swap_result['code'] == '0':
                swap_transaction_result = 1
                print("%s合约交易成功，本次交易张数为%s" % (ccy, swap_sz_str))
                
                spot_result = trade.set_order(instId=spot, tdMode='cross', side='buy', ordType='market', tgtCcy='base_ccy', sz=spot_sz_str)
                if spot_result['code'] == '0':
                   print("%s现货交易成功，本次交易个数为%s" % (ccy, spot_sz_str))
                   return 1
                else:
                   #此处要严重告警
                   print("%s现货交易失败，本次交易个数为%s" % (ccy, spot_sz_str))
                   print(spot_result)
            else:
                print("%s合约交易失败，本次交易张数为%s" % (ccy, swap_sz_str))
                print(swap_result)    #此处要严重告警
        else:
            print("%s合约交易成功，但是现货交易没成功，重试现货交易" % ccy)
            spot_result = trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=spot_sz_str)
            if spot_result['code'] == '0':
               print("%s现货卖出成功，本次交易个数为%s" % (ccy, spot_sz_str))
               return 1
            else:
               print("%s现货卖出失败，本次交易个数为%s" % (ccy, spot_sz_str))#此处要严重告警
               print(spot_result)

    return 0

def getRecentFundingRates(swap):
    '''
    获取永续合约交易对前10次的资金费率
    '''

    result = {}
    interval = 8 * 3600 * 1000 #费率每8小时更新一次
    cur = int(time.time()) * 1000
    cur = int(cur / interval) * interval
    start = cur - 10 * interval
    start = int(start / interval) * interval

    fundingRates = []
    result[swap] = {}

    ret = public.get_funding_rate_history(instId=swap, before=start, after=(cur+1)) #区间为[start, after)
    for j in ret['data']:
        fundingRates.append(float(j['fundingRate']))
        if int(j['fundingTime']) == cur:
            result[swap]['cur'] = float(j['fundingRate'])

    result[swap]['history'] = fundingRates
    result[swap]['avg'] = sum(fundingRates) / len(fundingRates)

    tmp = sorted(result.items(), key=lambda data: data[1]['avg'], reverse=True)
    result = {}
    for i in tmp:
        key = i[0]
        value = i[1]
        result[key] = value

    print(result)
    return result

def getDiscountRates():
    '''
    获取所有币种的折扣率
    '''

    result = {}

    instruments = public.get_instruments(instType='SWAP')
    instruments_code = instruments['code']
    instruments_data = instruments['data']

    data = public.get_discount_rate_interest_free_quota()
    code = data['code']
    data = data['data']

    for i in data:
        ccy = i['ccy']
        discountInfo = i['discountInfo']
        discountLv = int(i['discountLv'])

        amts = []
        for j in discountInfo:
            discountRate = float(j['discountRate'])
            minAmt = float(j['minAmt'])
            if len(j['maxAmt']):
                maxAmt = float(j['maxAmt'])
            else:
                maxAmt = float('inf')
            amts.append({'discountRate': discountRate, 'minAmt': minAmt, 'maxAmt': maxAmt})

        result[ccy] = {}
        result[ccy]['amt'] = amts

        for j in instruments_data:
            ccy_tmp = j['ctValCcy']

            if ccy_tmp == ccy:
                #合约面值
                result[ccy]['ct_val'] = j['ctVal']

    return result

def judgeCcyRisk(discountRates):
    '''
    根据币种对应的折扣率判断风险高中低：
    以5W美元为资金量，折扣率在[0,0.5)之间为高风险、[0.5,0.8)之间为中风险，0.8及以上为低风险
    '''

    amt = 50000
    highRisk = {}
    midRisk = {}
    lowRisk = {}

    for i in discountRates.keys():
        for j in discountRates[i]['amt']:
            if j['minAmt'] <= amt and amt <= j['maxAmt']:
                break
        else:
            print("%s不存在50000 USDT及以上的折扣率" % i)
            continue

        discountRate = j['discountRate']
        if 0 <= discountRate and discountRate < 0.5:
            highRisk[i] = discountRate
            discountRates[i]['risk'] = 'high'
        elif 0.5 <= discountRate and discountRate < 0.8:
            midRisk[i] = discountRate
            discountRates[i]['risk'] = 'mid'
        elif 0.8 <= discountRate:
            lowRisk[i] = discountRate
            discountRates[i]['risk'] = 'low'

    return highRisk, midRisk, lowRisk

def doOpenOrderTradeCondition(account, ccy, open_amount):
    '''
    判断当前币种是否开仓：
    1. 币种可开仓位＞100USDT
    2. 获取账户有效保证金及仓位价值，计算账户有效保证金/仓位价值≥40%
    3. 获取账户USDT币种权益，USDT币种权益≥10000USDT
    '''
    
    account_info = account.get_balance()
    code = account_info['code']
    data = account_info['data']

    adjEq = data[0]['adjEq']              #有效保证金 跨币种保证金模式和组合保证金模式
    notionalUsd = data[0]['notionalUsd']  #仓位价值

    if len(adjEq) != 0 and len(notionalUsd) != 0 and float(notionalUsd) != 0:
        val = float(adjEq) / float(notionalUsd)
        print("有效保证金/仓位价值%f，其中有效保证金%f, 仓位价值%f" % (val, float(adjEq), float(notionalUsd)))
        if val < 0.4:
            print("有效保证金/仓位价值{}≤40%，其中有效保证金{}, 仓位价值{}".format(val, float(adjEq), float(notionalUsd)))
            return False

    #检测usdt的
    details = data[0]['details']
    
    #USDT可用
    USDT_availEq = 0
    
    for i in details:
        ccy_tmp = i['ccy']
        if ccy_tmp == 'USDT':
            USDT_availEq = float(i['availEq'])
            if float(i['eq']) < USDT_EQ_LIMIT:
                print("USDT的币种权益(%f)不足开仓条件(%d)" % (float(i['eq']), USDT_EQ_LIMIT))
                return False

    for i in details:
        ccy_tmp = i['ccy']
        if ccy_tmp == ccy:
            eqUsd = float(i['eqUsd'])      #当前币的价值
            cashBal = float(i['cashBal'])  #币的数目
            print("当前%s仓位价值%f" % (ccy, eqUsd))
            if cashBal and float(open_amount - eqUsd) < float(eqUsd / cashBal):
                print("%s剩余可开金额%f不够，开一次需要%f" % (ccy, float(open_amount - eqUsd), float(eqUsd / cashBal)))
                return False
            else:
                if USDT_availEq and cashBal and float(eqUsd / cashBal) > USDT_availEq:
                    print("可用USDT(%f)不够%s开仓，开仓预计需要%d" % (USDT_availEq, ccy, float(eqUsd / cashBal)))
                    return False
                else:
                    return True

    return True

def doPositionBalanceMonitor(account, trade, ccy, discountRates):
    '''
    持仓平衡监控：
        当0.999≤现货持仓量/合约持仓量≤1.001时，视为仓位平衡，
        仓位如有不平衡，不可执行开仓交易，需平仓处理持仓量大的仓位，直至持仓平衡才可执行交易
    '''
    
    account_info = account.get_balance(ccy=ccy)
    code = account_info['code']
    data = account_info['data']
    
    if len(data[0]['details']) == 0:
        return True

    cashBal = data[0]['details'][0]['cashBal'] #币种余额

    swap = getSwapStr(ccy)
    spot = getSpotStr(ccy)
    positions_info = account.get_positions(instId=swap)
    code = positions_info['code']
    data = positions_info['data']
    
    if len(data) == 0:
        return True

    pos = data[0]['pos'] #币种持仓量
    
    if len(pos) and int(pos):
        swap_count = abs(int(pos)) * float(discountRates[ccy]['ct_val'])  #合约持仓量
        spot_count = float(cashBal) #现货持仓量
        balance = spot_count / swap_count
        print("%s合约持仓量%f, 现货持仓量%f, 平衡度%f" % (ccy, swap_count, spot_count, balance))
        if balance >= 0.999 and balance <= 1.001:
            return True
        else:
            if balance < 0.999:
                val = int((swap_count - spot_count) / float(discountRates[ccy]['ct_val']))
                if val > 0:
                    print("%s持仓不平衡，合约比现货多出张数%d,对多余部分进行处理" % (ccy, val))
                    #合约交易
                    swap_result = trade.set_order(instId=swap, tdMode='cross', side='buy', ordType='market', sz=str(val))
                    if swap_result['code'] != '0':
                        print("%s持仓不平衡,合约交易失败,信息如下：" % ccy)   #严重告警
                        print(swap_result)
                        return False
                    else:
                        print("%s持仓不平衡,合约交易成功" % ccy)
                        return True
                else:
                    print("%s持仓不平衡，但是合约多余不足一张，暂时不处理" % ccy)
            else:
                val = float(cashBal) - abs(int(pos)) * float(discountRates[ccy]['ct_val'])
                spot_result = trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=str(val))
                if spot_result['code'] != '0':
                    print("%s持仓不平衡,现货交易失败,信息如下：" % ccy)   #严重告警
                    print(spot_result)
                    return False
                else:
                    print("%s持仓不平衡,现货交易成功" % ccy)
                    return True

    return True

@log
def openOrder(key, secret, passphrase, flag, ccy, open_amount):

    account = Account(key=key, secret=secret, passphrase=passphrase, flag=flag)
    trade = Trade(key=key, secret=secret, passphrase=passphrase, flag=flag)

    swap = getSwapStr(ccy)

    fundingRates = getRecentFundingRates(swap)

    #获取折扣率 得到高风险低风险等级
    discountRates = getDiscountRates()
    judgeCcyRisk(discountRates)

    #开始执行策略
    #如果当前资金费率为负，则不开仓
    if fundingRates[swap]['cur'] <= 0:
        print("%s当前资金费率为负，不符合开仓条件" % ccy)
        exit()

    #确定开仓金额
    #open_amount = 50000 #默认5w
    #if discountRates[ccy]['risk'] == 'high':
    #    open_amount = 20000
    #elif discountRates[ccy]['risk'] == 'mid':
    #    open_amount = 50000
    #else:
    #    open_amount = 200000

    trade_count = 0

    while doOpenOrderTradeCondition(account, ccy, open_amount):
        ticker, code = getTicker(ccy, discountRates)
        if code != 0:
            print("%s价格重试多次后仍获取不到，暂停开仓操作" % ccy)  #严重告警
            break

        if False == isOpenOrderTradeCondsSatisfied(fundingRates[swap], ticker):
            continue

        if doPositionBalanceMonitor(account, trade, ccy, discountRates):
            ret = doOpenOrderTrade(trade, ccy, ticker)
            if ret == 0:
                print("%s开仓操作重试五次后仍失败" % ccy)  #严重告警
                exit()    #严重告警
            else:
                trade_count = trade_count + 1
        else:
            break
        
        #避免限频，交易10次后停5s
        if trade_count == 10:
            time.sleep(5)

    trade_count = 0

    #交易完成后再做一次仓位平衡计算
    doPositionBalanceMonitor(account, trade, ccy, discountRates)


def isClearanceTradeCondsSatisfied(account, trade, ccy, ticker):
    '''
    判断当前币种是否满足交易条件：
    1. （合约卖1价-现货买1价）/现货买1价≤0.0005
    2. 持仓价值>= 200
    '''

    if (ticker['swap_sell'] - ticker['spot_buy']) / ticker['spot_buy'] <= CLEARANCE_CONDITION:
        account_info = account.get_balance(ccy=ccy)
        code = account_info['code']
        data = account_info['data']

        if len(data[0]['details']) == 0:
            return False

        cashBal = data[0]['details'][0]['cashBal']   #币种余额
        eqUsd = data[0]['details'][0]['eqUsd']       #币种美元
        if float(eqUsd) >= 200:
            return True
        else:
            #清仓流程
            spot = getSpotStr(ccy)
            swap = getSwapStr(ccy)
            trade.set_close_position(instId=swap, mgnMode='cross')
            trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=cashBal)
            print("最后不足200u的%s币种价值，清仓" % ccy)
            return False
    else:
        print("清仓条件不满足 合约卖1价(%f)-现货买1价(%f) / 现货买1价(%f) ≤ 0.0005", (ticker['swap_sell'], ticker['spot_buy'], ticker['spot_buy']))
        return False

def doClearanceTrade(key, secret, passphrase, flag, ccy, ticker):
    '''
    执行交易
    '''

    account = Account(key=key, secret=secret, passphrase=passphrase, flag=flag)
    trade = Trade(key=key, secret=secret, passphrase=passphrase, flag=flag)

    spot = getSpotStr(ccy)
    swap = getSwapStr(ccy)

    #合约交易张数
    swap_sz_str = str(ticker['swap_sz'])
    #现货交易金额
    spot_sz_str = str(ticker['spot_sz'])

    swap_transaction_result = 0

    for i in range(5):
        if swap_transaction_result == 0:
            swap_result = trade.set_order(instId=swap, tdMode='cross', side='buy', ordType='market', sz=swap_sz_str) #合约交易
            if swap_result['code'] == '0':
                print("合约平仓成功，本次交易张数为%s" % swap_sz_str)
                swap_transaction_result = 1

                spot_result = trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=spot_sz_str)
                if spot_result['code'] == '0':
                    print("现货卖出成功，本次交易个数为%s" % spot_sz_str)
                    return 1
                else:
                    print("现货卖出失败，本次交易个数为%s，按照可用值来交易看看" % spot_sz_str)
                    print(spot_result)
                    account_info = account.get_balance(ccy=ccy)
                    code = account_info['code']
                    data = account_info['data']

                    availBal = data[0]['details'][0]['availBal']   #币种可用余额
                    if float(availBal) < float(ticker['spot_sz']):
                        spot_sz_str = str(availBal)
                        spot_result = trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=spot_sz_str)
                        if spot_result['code'] == '0':
                            print("现货卖出成功，本次交易个数为%s" % spot_sz_str)
                            return 1
                        else:
                            print("现货卖出失败，本次交易个数为%s" % spot_sz_str)#此处要严重告警
                            print(spot_result)
            else:
                print("合约平仓失败，本次交易张数为%s" % swap_sz_str)
                print(swap_result)    #此处要严重告警
        else:
            print("合约交易成功，但是现货交易没成功，重试现货交易")
            account_info = account.get_balance(ccy=ccy)
            code = account_info['code']
            data = account_info['data']

            availBal = data[0]['details'][0]['availBal']   #币种可用余额
            if availBal < ticker['spot_sz']:
                spot_sz_str = str(availBal)
            spot_result = trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=spot_sz_str)
            if spot_result['code'] == '0':
               print("现货卖出成功，本次交易个数为%s" % spot_sz_str)
               return 1
            else:
               print("现货卖出失败，本次交易个数为%s" % spot_sz_str)#此处要严重告警
               print(spot_result)

    return 0

#清仓 输入币种，例如"AIDOGE"
@log
def ccyClearance(key, secret, passphrase, flag, ccy):

    account = Account(key=key, secret=secret, passphrase=passphrase, flag=flag)
    trade = Trade(key=key, secret=secret, passphrase=passphrase, flag=flag)

    discountRates = getDiscountRates()

    while True:
        ticker, code = getTicker(ccy, discountRates)
        if code != 0:
            print("%s价格重试多次后仍获取不到，暂停平仓操作" % ccy)  #严重告警
            break

        if isClearanceTradeCondsSatisfied(account, trade, ccy, ticker):
            ret = doClearanceTrade(key, secret, passphrase, flag, ccy, ticker)
            if ret == 0:
                print("%s平仓操作重试五次后仍失败" % ccy)  #严重告警
        else:
            break


def getCurrentSwap(account):
    '''
    获取持仓币种
    '''
    positions_info = account.get_positions(instType='SWAP')
    code = positions_info['code']

    swaps = []
    for i in positions_info['data']:
        swaps.append(i['instId'])
        
    return swaps

def showCurrentAccountFundingRates(fundingRates):
    '''
    按照从大到小的顺序显示所有合约交易对的资金费率
    '''

    j = 0

    print("%20s %20s %20s" % ('SWAP', 'AVG', 'CURRENT'))#, 'HISTORY'))
    for i in fundingRates.keys():
        print("%20s %20f %20f" % (i, fundingRates[i]['avg'], fundingRates[i]['cur']))
        j = j + 1
        if j == 10:
            return
        #print(fundingRates[i]['history'])

def getCurrentPositionsFundingRates(swaps):
    '''
    获取持仓的资金费率
    '''

    fundingRates = getRecent10FundingRates(swaps)
    showCurrentAccountFundingRates(fundingRates)
    
    return fundingRates

def getSwapsDiscountRates(swaps):
    '''
    获取所有币种的折扣率
    '''

    result = {}
    public = Public()

    instruments = public.get_instruments(instType='SWAP')
    instruments_code = instruments['code']
    instruments_data = instruments['data']

    data = public.get_discount_rate_interest_free_quota()
    code = data['code']
    data = data['data']

    has_key = 0

    for i in data:
        ccy = i['ccy']
        discountInfo = i['discountInfo']
        discountLv = int(i['discountLv'])

        for k in swaps:
            ccy_tmp = getCcyStr(k)
            if ccy == ccy_tmp:
                has_key = 1

        if has_key == 0:
            continue

        has_key = 0

        amts = []
        for j in discountInfo:
            discountRate = float(j['discountRate'])
            minAmt = float(j['minAmt'])
            if len(j['maxAmt']):
                maxAmt = float(j['maxAmt'])
            else:
                maxAmt = float('inf')
            amts.append({'discountRate': discountRate, 'minAmt': minAmt, 'maxAmt': maxAmt})

        result[ccy] = {}
        result[ccy]['amt'] = amts

        for j in instruments_data:
            ccy_tmp = j['ctValCcy']

            if ccy_tmp == ccy:
                #合约面值
                result[ccy]['ct_val'] = j['ctVal']

    return result

def judgeCcyRiskMonitor(discountRates):
    '''
    根据币种对应的折扣率判断风险高中低：
    以5W美元为资金量，折扣率在[0,0.5)之间为高风险、[0.5,0.8)之间为中风险，0.8及以上为低风险
    '''

    amt = 50000
    highRisk = {}
    midRisk = {}
    lowRisk = {}

    for i in discountRates.keys():
        for j in discountRates[i]['amt']:
            if j['minAmt'] <= amt and amt <= j['maxAmt']:
                break
        else:
            print("%s不存在50000 USDT及以上的折扣率" % i)
            continue

        discountRate = j['discountRate']
        if 0 <= discountRate and discountRate < 0.5:
            highRisk[i] = discountRate
            discountRates[i]['risk'] = RISK['high']
        elif 0.5 <= discountRate and discountRate < 0.8:
            midRisk[i] = discountRate
            discountRates[i]['risk'] = RISK['mid']
        elif 0.8 <= discountRate:
            lowRisk[i] = discountRate
            discountRates[i]['risk'] = RISK['low']

    discountRates = sorted(discountRates.items(), key=lambda discountRates: discountRates[1]['risk'], reverse=True)

    return highRisk, midRisk, lowRisk

def checkAdjEq(account):
    '''
    判断当前币种是否开仓：
    1. 币种可开仓位＞100USDT
    2. 获取账户有效保证金及仓位价值，计算账户有效保证金/仓位价值≥40%
    3. 获取账户USDT币种权益，USDT币种权益≥10000USDT
    '''
    
    account_info = account.get_balance()
    code = account_info['code']
    data = account_info['data']
    
    adjEq = data[0]['adjEq']              #有效保证金 跨币种保证金模式和组合保证金模式
    notionalUsd = data[0]['notionalUsd']  #仓位价值

    global global_do_deordering

    if len(adjEq) != 0 and len(notionalUsd) != 0 and notionalUsd != 0:
        val = float(adjEq) / float(notionalUsd)
        print("[风控检测]当前有效保证金/仓位价值%f，其中有效保证金%f, 仓位价值%f" % (val, float(adjEq), float(notionalUsd)))
        if val < EFFECTIVE_MARGIN_RATIO_ERR:
            global_do_deordering = 1
            print("[风控检测]当前有效保证金/仓位价值低于%f,开始平仓" % float(EFFECTIVE_MARGIN_RATIO_ERR))
            return False

    if global_do_deordering == 1:
        val = float(adjEq) / float(notionalUsd)
        print("[风控检测]正在平仓中, 当前有效保证金/仓位价值为%f" % val)
        if val > EFFECTIVE_MARGIN_RATIO_LIMIT:
            print("[风控检测]当前有效保证金/仓位价值高于%f, 停止平仓" % float(EFFECTIVE_MARGIN_RATIO_LIMIT))
            global_do_deordering = 0
            return True
        else:
            return False

    return True

def getClosePositionTicker(ccy, discountRates):
    '''
    获取币种现货卖1价和合约买1价
    '''

    #获取
    spot = ccy + '-' + CASH
    swap = spot + '-SWAP'
    
    result = {}
    ret = market.get_ticker(instId=spot)
    result['spot_buy'] = float(ret['data'][0]['askPx']) #askPx为买一价
    result['spot_sell'] = float(ret['data'][0]['bidPx']) #askPx为卖一价
    ret = market.get_ticker(instId=swap)
    result['swap_buy'] = float(ret['data'][0]['askPx']) #askPx为买一价
    result['swap_sell'] = float(ret['data'][0]['bidPx']) #bidPx为卖一价
    
    current_swap_val = float(result['swap_buy'])

    #计算出开合约的张数 100u/当前价格 然后除以合约面值 得到合约张数
    result['swap_sz'] = int(TRADE_BASE_AMOUNT / current_swap_val / float(discountRates[ccy]['ct_val']))
    result['spot_sz'] = result['swap_sz'] * float(discountRates[ccy]['ct_val'])

    return result

def doClosePositionTrade(account, trade, ccy, ticker):
    '''
    执行交易
    '''

    spot = getSpotStr(ccy)
    swap = getSwapStr(ccy)

    #合约交易张数
    swap_sz_str = str(ticker['swap_sz'])
    #现货交易金额
    spot_sz_str = str(ticker['spot_sz'])

    swap_transaction_result = 0

    for i in range(5):
        if swap_transaction_result == 0:
            swap_result = trade.set_order(instId=swap, tdMode='cross', side='buy', ordType='market', sz=swap_sz_str) #合约交易
            if swap_result['code'] == '0':
                print("[风控处理]%s合约平仓成功，本次交易张数为%s" % (ccy, swap_sz_str))
                swap_transaction_result = 1

                spot_result = trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=spot_sz_str)
                if spot_result['code'] == '0':
                    print("[风控处理]%s现货卖出成功，本次交易个数为%s" % (ccy, spot_sz_str))
                    return 1
                else:
                    print("[风控处理]%s现货卖出失败，本次交易个数为%s，按照可用值来交易看看" % (ccy, spot_sz_str))
                    print(spot_result)
                    account_info = account.get_balance(ccy=ccy)
                    code = account_info['code']
                    data = account_info['data']

                    availBal = data[0]['details'][0]['availBal']   #币种可用余额
                    if float(availBal) < float(ticker['spot_sz']):
                        spot_sz_str = str(availBal)
                        spot_result = trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=spot_sz_str)
                        if spot_result['code'] == '0':
                            print("[风控处理]%s现货卖出成功，本次交易个数为%s" % (ccy, spot_sz_str))
                            return 1
                        else:
                            print("[风控处理]%s现货卖出失败，本次交易个数为%s" % (ccy, spot_sz_str))#此处要严重告警
                            print(spot_result)
            else:
                print("[风控处理]%s合约平仓失败，本次交易张数为%s" % (ccy, swap_sz_str))
                print(swap_result)    #此处要严重告警
        else:
            print("[风控处理]%s合约交易成功，但是现货交易没成功，重试现货交易" % ccy)
            account_info = account.get_balance(ccy=ccy)
            code = account_info['code']
            data = account_info['data']

            availBal = data[0]['details'][0]['availBal']   #币种可用余额
            if availBal < ticker['spot_sz']:
                spot_sz_str = str(availBal)
            spot_result = trade.set_order(instId=spot, tdMode='cross', side='sell', ordType='market', tgtCcy='base_ccy', sz=spot_sz_str)
            if spot_result['code'] == '0':
               print("[风控处理]%s现货卖出成功，本次交易个数为%s" % (ccy, spot_sz_str))
               return 1
            else:
               print("[风控处理]%s现货卖出失败，本次交易个数为%s" % (ccy, spot_sz_str))#此处要严重告警
               print(spot_result)

    return 0

@log
def doMonitor(key, secret, passphrase, flag):

    account = Account(key=key, secret=secret, passphrase=passphrase, flag=flag)
    trade = Trade(key=key, secret=secret, passphrase=passphrase, flag=flag)

    #获取当前持仓币种
    swaps = getCurrentSwap(account)

    print(swaps)

    #获取当前持仓币种的资金费率
    fundingRates = getCurrentPositionsFundingRates(swaps)

    #获取折扣率 得到高风险低风险等级
    discountRates = getSwapsDiscountRates(swaps)
    judgeCcyRiskMonitor(discountRates)

    print(discountRates)

    while True:
        trade_count = 0

        while checkAdjEq(account) == False:
        
            ccy = ''
            for i in swaps:
                positions_info = account.get_positions(instId=i)
                code = positions_info['code']
                data = positions_info['data']

                if len(data) == 0:
                    continue

                pos = data[0]['pos']
                if len(pos) == 0:
                    continue

                if int(pos) == 0:
                    continue

                ccy = getCcyStr(i)
                break

            if len(ccy) == 0:
               print("[风控监控]进入平仓操作，却又没检测到币种。严重告警")
               continue

            #进入风控平仓流程
            ticker = getClosePositionTicker(ccy, discountRates)
            ret = doClosePositionTrade(account, trade, ccy, ticker)
            if ret == 0:
                print("[风控监控]平仓操作重试五次后仍失败。严重告警")
            
            #避免限频，交易10次后停5s
            if trade_count == 10:
                time.sleep(5)

        trade_count = 0
        time.sleep(5)


@log
def monitor_once(key, secret, passphrase, flag):
    print(key)
    return
    account = Account(key=key, secret=secret, passphrase=passphrase, flag=flag)
    trade = Trade(key=key, secret=secret, passphrase=passphrase, flag=flag)

    #获取当前持仓币种
    swaps = getCurrentSwap(account)

    print(swaps)

    #获取当前持仓币种的资金费率
    fundingRates = getCurrentPositionsFundingRates(swaps)

    #获取折扣率 得到高风险低风险等级
    discountRates = getSwapsDiscountRates(swaps)
    judgeCcyRiskMonitor(discountRates)

    print(discountRates)

    trade_count = 0

    while checkAdjEq(account) == False:
    
        ccy = ''
        for i in swaps:
            positions_info = account.get_positions(instId=i)
            code = positions_info['code']
            data = positions_info['data']

            if len(data) == 0:
                continue

            pos = data[0]['pos']
            if len(pos) == 0:
                continue

            if int(pos) == 0:
                continue

            ccy = getCcyStr(i)
            break

        if len(ccy) == 0:
            print("[风控监控]进入平仓操作，却又没检测到币种。严重告警")
            continue

        #进入风控平仓流程
        ticker = getClosePositionTicker(ccy, discountRates)
        ret = doClosePositionTrade(account, trade, ccy, ticker)
        if ret == 0:
            print("[风控监控]平仓操作重试五次后仍失败。严重告警")
        
        #避免限频，交易10次后停5s
        if trade_count == 10:
            time.sleep(5)



if __name__ == '__main__':
    print('====debug====')
    # getRecent10FundingRatesMax()
    # getCurrentAccountFundingRatesFlow(KEY, SECRET, PASSPHRASE, FLAG)
    # doMonitor(KEY, SECRET, PASSPHRASE, FLAG)
    