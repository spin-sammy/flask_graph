import numpy as np
import ccxt
from datetime import datetime, time
import pandas as pd
import config
import pandas_ta as ta
import time
from pprint import pprint

pair = 'XRPUSDT'
time_frame = '5m'
pair_num = 0
candle_limit = 201
SMA_window = 21
EMA_window = 201
ATR_window = 5
CCI_window = 50
ST_window = 10
ST_multi = 3.0
ST_window2 = 5
ST_multi2 = 3.0
MACD_fast = 12
MACD_slow = 26
MACD_signal = 9
df = ''
df_i = ''
max_i_w = 0
delta_df = 0
sell_flag = False
buy_flag = False
size = 9.0
ema_angle = 0
ema_angle_limit = 0.0002
ema_angle_candles = 50


exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': config.a_key,
    'secret': config.a_secret,
    'timeout': 30000,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

print('Баланс в USDT: {}'.format(
    exchange.fetch_balance()['USDT']['total']))  # Выводит баланс фьючерсного кошелька в USDT/BUSD/BNB
print('Свободно: {}'.format(
    exchange.fetch_balance()['USDT']['free']))  # 'total' - всего, 'free' - свободно, 'used' - используется
print('Используется: {}'.format(exchange.fetch_balance()['USDT']['used']))

pos = exchange.fetch_balance()['info']['positions']

for i in range(len(pos)):
    if pos[i]['symbol'] == pair:
        pair_num = i
print(f'Пара: {pair} ({pair_num})')


def read_pair_data(pair):  # ЧИТАЕМ ДАННЫЕ ПАРЫ

    global df, delta_df, df_i, max_i_w
    # Создаем датафрейм -------------------------------------------------------------------------
    max_i_w = max(SMA_window, EMA_window, ATR_window, CCI_window)
    bars_i = exchange.fetch_ohlcv(pair, timeframe=time_frame,
                                  limit=candle_limit + max_i_w)  # Выводит limit минутных свечей
    bars = exchange.fetch_ohlcv(pair, timeframe=time_frame, limit=candle_limit)  # Выводит limit минутных свечей
    df_i = pd.DataFrame(bars_i, columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df = pd.DataFrame(bars, columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
    delta_df = len(df_i) - len(df)

    # Заменяем timestamp на время UTC в датафрейме df_i[] ---------------------------------------
    df_i['Datetime'] = [datetime.fromtimestamp(x / 1000) for x in df_i['Datetime']]
    # -------------------------------------------------------------------------------------------

    # Индикатор тренда RSI ----------------------------------------------------------------------
    # ta.rsi(df['Close'], 14)
    # -------------------------------------------------------------------------------------------

    # Индикатор тренда SMA ----------------------------------------------------------------------
    df_i['Sma'] = ta.sma(df_i['Close'], SMA_window)
    # -------------------------------------------------------------------------------------------

    # Индикатор тренда EMA ----------------------------------------------------------------------
    df_i['Ema'] = ta.ema(df_i['Close'], EMA_window)
    # -------------------------------------------------------------------------------------------

    # Индикатор волатильности ATR ---------------------------------------------------------------
    df_i['Atr'] = ta.atr(df_i['High'], df_i['Low'], df_i['Close'], ATR_window)
    # -------------------------------------------------------------------------------------------

    # Индикатор тренда CCI ----------------------------------------------------------------------
    df_i['Cci'] = ta.cci(df_i['High'], df_i['Low'], df_i['Close'], CCI_window)
    # -------------------------------------------------------------------------------------------

    # Индикатор тренда MACD ---------------------------------------------------------------------
    macd = ta.macd(df_i['Close'], MACD_fast, MACD_slow, MACD_signal)
    df_i['Macd'] = macd['MACD_' + str(MACD_fast) + '_' + str(MACD_slow) + '_' + str(MACD_signal)]
    df_i['Macd_h'] = macd['MACDh_' + str(MACD_fast) + '_' + str(MACD_slow) + '_' + str(MACD_signal)]
    df_i['Macd_s'] = macd['MACDs_' + str(MACD_fast) + '_' + str(MACD_slow) + '_' + str(MACD_signal)]
    # -------------------------------------------------------------------------------------------

    # Индикатор тренда Supertrend _--------------------------------------------------------------
    st = ta.supertrend(df_i['High'], df_i['Low'], df_i['Close'], ST_window, ST_multi)
    df_i['St'] = st['SUPERT_' + str(ST_window) + '_' + str(ST_multi)]
    df_i['St_d'] = st['SUPERTd_' + str(ST_window) + '_' + str(ST_multi)]
    # -------------------------------------------------------------------------------------------

    # Индикатор тренда Supertrend _--------------------------------------------------------------
    st = ta.supertrend(df_i['High'], df_i['Low'], df_i['Close'], ST_window2, ST_multi2)
    df_i['St2'] = st['SUPERT_' + str(ST_window2) + '_' + str(ST_multi2)]
    df_i['St_d2'] = st['SUPERTd_' + str(ST_window2) + '_' + str(ST_multi2)]
    # -------------------------------------------------------------------------------------------

    df = df_i[delta_df:]
    df.index = np.arange(len(df))


def check_pos():
    global buy_flag, sell_flag, pos, df
    pos = exchange.fetch_balance()['info']['positions'][pair_num]

    if pos['positionAmt'] == '0.000':
        exchange.cancelAllOrders(pair)
        sell_flag, buy_flag = False, False
        time.sleep(2)

    if buy_flag and df['St_d'][candle_limit - 1] == -1:
        exchange.create_order(symbol=pair, type='market', side='sell', amount=size, params={'reduce_only': True})
        time.sleep(0.2)
        exchange.cancelAllOrders(pair)
        buy_flag = False

    if sell_flag and df['St_d'][candle_limit - 1] == 1 and pos:
        exchange.create_order(symbol=pair, type='market', side='buy', amount=size, params={'reduce_only': True})
        time.sleep(0.2)
        exchange.cancelAllOrders(pair)
        sell_flag = False

def strategy():
    global buy_flag, sell_flag, ema_angle
    last_candle = candle_limit - 1
    ema_angle = max(df_i['Ema'][-ema_angle_candles:]) - min(df_i['Ema'][-ema_angle_candles:])

    if df['Close'][last_candle] > df['Ema'][last_candle] and not buy_flag \
            and ema_angle > ema_angle_limit:  # buy
        if last_candle >= 1 and df['Macd'][last_candle] > df['Macd_s'][last_candle] \
                and df['St_d'][last_candle] > 0:
            open_buy_market_order(pair=pair, size=size, stop_price=df['St'][last_candle])


    if df['Close'][last_candle] < df['Ema'][last_candle] and not sell_flag \
            and ema_angle > ema_angle_limit:  # short
        if last_candle >= 1 and df['Macd'][last_candle] < df['Macd_s'][last_candle] \
                and df['St_d'][last_candle] < 0:
            open_sell_market_order(pair=pair, size=size, stop_price=df['St'][last_candle])


def open_buy_market_order(pair, size, stop_price):
    global buy_flag
    try:
        order = exchange.create_order(symbol=pair, type='market', side='buy', amount=size)
        print(f'Позиция BUY {pair} успешно открыта.')
        print(order)
        time.sleep(0.5)
        stop_order = exchange.create_order(symbol=pair, type='stop_market',
                                           side='sell', amount=size, params={'stopPrice': stop_price})
        print(f'Успешно установлен стоп-ордер {stop_price}.')
        print(stop_order)
        buy_flag = True
        return True

    except Exception as e:
        exchange.cancelAllOrders(pair)
        print('Не удалось открыть позицию на покупку!')
        print(f'Ошибка: {format(e)}')
        buy_flag = False
        return False


def open_sell_market_order(pair, size, stop_price):
    global sell_flag
    try:
        order = exchange.create_order(symbol=pair, type='market', side='sell', amount=size)
        print(f'Позиция SELL {pair} успешно открыта.')
        print(order)
        time.sleep(0.5)
        stop_order = exchange.create_order(symbol=pair, type='stop_market',
                                           side='buy', amount=size, params={'stopPrice': stop_price, })
        print(f'Успешно установлен стоп-ордер {stop_price}.')
        print(stop_order)
        sell_flag = True
        return True

    except Exception as e:
        exchange.cancelAllOrders(pair)
        print('Не удалось открыть позицию на продажу!')
        print(f'Ошибка: {format(e)}')
        sell_flag = False
        return False


old_time = '00:00:00'
while True:
    current_time = str(datetime.now().time())
    if current_time[4] != old_time[4]:  # Проверяем паттерны каждую минуту
        check_pos()
        time.sleep(0.5)
        read_pair_data(pair)
        # print(df)
        print(str(datetime.now().time())[:8])
        if not sell_flag and not buy_flag:
            strategy()
        print(f'Позиция: {pos["positionAmt"]} угол EMA: {round(ema_angle, 5)} лимит: {ema_angle_limit} Sell: {sell_flag} Buy: {buy_flag}')
        print(f'EMA: {round(df["Ema"][candle_limit-1], 5)} MACD: {round(df["Macd"][candle_limit-1], 5)} MACD_s: {round(df["Macd_s"][candle_limit-1],5)}')

    old_time = current_time
