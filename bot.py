# Prototype built in this note book
# -->  bot.py is the actual tradeing bot
# -->  dashboard.py to visualize candles, balances and trades
# Thanks to parttimelarry (hackingthemarkets.com) for inspiration and awesome tutorials

import os, csv, datetime, websocket, json, pprint
from binance.client import Client 
from binance.enums import *
import numpy as np
import pandas as pd
import pandas_ta as pta
#import talib
#import backtrader as bt
import config
import pickle
import datetime
from tradingview_ta import TA_Handler, Interval

# Initialise the API client
client = Client(config.API_KEY, config.API_SECRET)

### STRATEGY FUNCTIONS

# To get recommendation from Tradingview api
def tradingview_rec(coin_pair, period):
    coin = TA_Handler()
    coin.set_symbol_as(coin_pair)
    coin.set_exchange_as_crypto_or_stock("BINANCE")
    coin.set_screener_as_crypto()
    
    if period == "hour":
        coin.set_interval_as(Interval.INTERVAL_1_HOUR)
    if period == "day":
        coin.set_interval_as(Interval.INTERVAL_1_DAY)
    elif period == "week":
        coin.set_interval_as(Interval.INTERVAL_1_WEEK)
    rec = coin.get_analysis().summary
    rec.update({"COIN_PAIR": coin_pair})
    rec.update({"PERIOD": period})
    
    return rec


def my_strategy(df, coin_pair, period):
    
    ### SETTINGS ###
    MA_PERIOD      = 50
    MA_OFFSET_SELL = 1
    MA_OFFSET_BUY  = 1
    RSI_PERIOD     = 14
    RSI_OVERBOUGHT = 75
    RSI_OVERSOLD   = 25
    
    df["c"] = df["c"].astype(float)
    # Current price
    last_close = df["c"].iloc[-1]
    print(f"strategy looks at: {last_close}")
    
    # MA
    df["ma"] = df["c"].rolling(window=MA_PERIOD).mean()
    last_ma = df["ma"].iloc[-1]
    
    # RSI
    rsi = pta.rsi(df["c"], length=RSI_PERIOD)
    last_rsi = rsi.iloc[-1].round(1)
    
    # Get TradingView recommendation
    tradingview_say = tradingview_rec(coin_pair, period)
    if tradingview_say["RECOMMENDATION"] == "BUY" or tradingview_say["RECOMMENDATION"] == "STRONG_BUY" :
        tradingview_buy = True 
    elif tradingview_say["RECOMMENDATION"] == "SELL" or tradingview_say["RECOMMENDATION"] == "STRONG_SELL" :
        tradingview_buy = False
        
    # Conditions for 'sell' or 'buy' or 'wait'
    if (last_rsi > RSI_OVERBOUGHT or last_close < (last_ma * MA_OFFSET_SELL)) and tradingview_buy == False:
        print(f"the current rsi_{RSI_PERIOD} is: ", last_rsi)
        print(f"the current ma_{MA_PERIOD} is: ", last_ma)
        print("tradingview say: ", tradingview_say["RECOMMENDATION"])
        
        return "sell"
    
    
    elif (last_rsi < RSI_OVERSOLD or last_close > (last_ma * MA_OFFSET_BUY)) and tradingview_buy == True:
        print(f"the current rsi_{RSI_PERIOD} is", last_rsi)
        print(f"the current ma_{MA_PERIOD} is", last_ma)
        print("tradingview say: ", tradingview_say["RECOMMENDATION"])
        
        return "buy"
    
    
    else:
        print(f"the current rsi_{RSI_PERIOD} is", last_rsi)
        print(f"the current ma_{MA_PERIOD} is", last_ma)
        print("tradingview say: ", tradingview_say["RECOMMENDATION"])
        
        return "wait"
    
    
### To place order for Binance api
def order(side, quantity, symbol,order_type=ORDER_TYPE_MARKET):
    try:
        print("sending order")
        order = client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
        print(order)
    except Exception as e:
        print("an exception occured - {}".format(e))
        return False

    return True


### NOTE SETTINGS --> RUNNNG THE BOT ###

### SETTINGS ###
MIN_START_TIME_PERODS = 14       # Start trading after this num of periods (candles)
TARGET_PERIOD = "hour"           # Used bt tradingWiew api to get recommendations (hour/day/week)
TRADE_SYMBOL = "ETHUSDT"
TIME_RESOLUTION = "5m"           # note its related to TA-indicators (MA/RSI)
PLACE_LIVE_ORDER = False         # FALSE mean no order will be placed (but still visualized)
TRADE_QUANTITY = 0.5             # how much to trade (crypto coins)

START_CAPITAL = 10_000               # USDT

SOCKET = f"wss://stream.binance.com:9443/ws/{TRADE_SYMBOL.lower()}@kline_{TIME_RESOLUTION}"

# Initiate list of candle sequences, sells, buys and balance
candles = []

# init lists - to check and visualize performance and earnings
sells = []
buys = []

balances_usdt_lst = []
balances_coin_lst = []
in_position = False # at start, modified after order

balance_usdt = START_CAPITAL  # modified depending on trades
balance_coin = 0  # modified depending on trades

client = Client(config.API_KEY, config.API_SECRET)

def on_open(ws):
    print('open connection')

def on_close(ws):
    print('close connection')

def on_message(ws, message):
    global closes, in_position, balance_usdt, balance_coin # since function is called on message
    
    #print('received message')
    json_message = json.loads(message)
    candle = json_message['k']

    candle_closed = candle['x']
    close = candle['c']

    if candle_closed:
        print("--------------")
        print(f"Candle closed at {close}")
        print(f"In position: {in_position}")
        print(f"balance_usdt: {balance_usdt}")
        print(f"balance_coin: {balance_coin}, value: {balance_coin * float(close)} usd")
            
        candles.append(candle)
        df = pd.DataFrame(candles)
        
        print("shape of df", df.shape)
        print("df mem: ", df.memory_usage(deep=True).sum())
        print("UTC Time: ", datetime.datetime.utcnow())
        

        if len(candles) > MIN_START_TIME_PERODS:
            
            try:
                strategy = my_strategy(df, TRADE_SYMBOL, TARGET_PERIOD)
                print("Strategy say: ", strategy)
            except Exception as e:
                print("hmm, an exception occured - {}".format(e))
   
            if strategy == "sell":
                if in_position:
                    #binance sell logic
                    if PLACE_LIVE_ORDER == True:
                        print("I AM SELLING 'LIVE' !")
                        order_succeeded = order(SIDE_SELL, TRADE_QUANTITY, TRADE_SYMBOL)
                        if order_succeeded:
                            in_position = False
                            
                    elif PLACE_LIVE_ORDER == False:
                        print("I AM SELLING 'TEST' !")
                        in_position = False
                    
                    # append time and price to buy list
                    sells.append({df["T"].iloc[-1]: df["c"].iloc[-1]})
                    
                    # append to balances lists
                    balance_usdt = balance_usdt + (float(close) * TRADE_QUANTITY)
                    balances_usdt_lst.append({df["T"].iloc[-1]: balance_usdt})
                    print("sold, - balance usdt (added to lst)", balance_usdt)
                    balance_coin =  balance_coin - TRADE_QUANTITY
                    balances_coin_lst.append({df["T"].iloc[-1]: balance_coin * float(close)})
                    print("sold, - balance coin (added to lst)", balance_coin)
                    
                else:
                    print("Sell Signal. But Not In Position ")
            
            
            if strategy == "buy":
                if in_position:
                    print("Buy Signal. But Already In Position")
                    
                else:
                    #binance buy order logic
                    if PLACE_LIVE_ORDER == True:
                        print("I AM BUYING 'LIVE' !")
                        order_succeeded = order(SIDE_BUY, TRADE_QUANTITY, TRADE_SYMBOL)
                        if order_succeeded:
                            in_position = True 
                            
                    elif PLACE_LIVE_ORDER == False:
                        print("I AM BUYING 'TEST' !")
                        in_position = True
                        
                    # append time and price to buy list
                    buys.append({df["T"].iloc[-1]: df["c"].iloc[-1]})
                    
                    # append to balances lists
                    balance_usdt = balance_usdt - (float(close) * TRADE_QUANTITY)
                    balances_usdt_lst.append({df["T"].iloc[-1]: balance_usdt})
                    print("bought, - balance usdt (added to lst)", balance_usdt)
                    balance_coin =  balance_coin + TRADE_QUANTITY
                    balances_coin_lst.append({df["T"].iloc[-1]: balance_coin * float(close)})
                    print("bought, - balance coin (added to lst)", balance_coin)
                        
            # Save df to be visualized in real time web app
            print("saving df..")
            df.to_csv(f"data/{SOCKET[41:]}_{TRADE_SYMBOL}.csv")
            print("df saved")
            pickle.dump(sells, open("data/sells.p", "wb"))
            pickle.dump(buys, open("data/buys.p", "wb"))
            pickle.dump(balances_usdt_lst, open("data/balances_usdt_lst.p", "wb"))
            pickle.dump(balances_coin_lst, open("data/balances_coin_lst.p", "wb"))
            pickle.dump([balance_usdt, balance_coin, START_CAPITAL], open("data/current_balance.p", "wb"))
            print("all buy/sell/balances lists saved")

                
ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever() 