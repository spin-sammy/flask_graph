import pandas_ta as ta
import config
import pandas as pd
import ccxt
from datetime import datetime, time
import time

exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': config.a_key,
    'secret': config.a_secret,
    'timeout': 30000,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

pair = 'BCHUSDT'
time_frame = '1m'
candle_limit = 300
bars = exchange.fetch_ohlcv(pair, timeframe=time_frame, limit=candle_limit)  # Выводит limit минутных свечей

st_window = 12
st_multi = 3

df = pd.DataFrame(bars, columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
st = ta.supertrend(df['High'], df['Low'], df['Close'], st_window, st_multi)
sma = ta.sma(df['Close'], 8)
ema = ta.ema(df['Close'], 15)
atr = ta.atr(df['High'], df['Low'], df['Close'], 12)
macd = ta.macd(df['Close'], 12, 24, 3)
#print(macd)
#print(st['SUPERT_'+str(st_window)+'_'+str(st_multi)+'.0'])

#pos = exchange.fetch_balance()['info']['positions']

#print(pos)

# stopLossParams = {'closePosition': True, 'stopPrice': 0.8, 'reduce_only': True}
# exchange.create_order('XRPUSDT', 'STOP_MARKET', 'buy', 100, None, stopLossParams)
#
# takeProfitParams = {'closePosition': True, 'stopPrice': 0.7722, 'reduce_only': True}
# exchange.create_order('XRPUSDT', 'TAKE_PROFIT_MARKET', 'buy', 100, None, takeProfitParams)
#
# exchange.create_order('XRPUSDT', 'MARKET', 'sell', 100)

order = exchange.fetch_open_orders(pair)

print(order)
print(len(order))

t = int(str(datetime.now().time())[0:2])
print(t)


if t >= 4 and t <= 20:
    print('Можно торговать!')
else:
    print('Торговать нельзя!')