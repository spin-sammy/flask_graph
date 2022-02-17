import numpy as np
import ccxt
from datetime import datetime, time
import pandas as pd
import config
import pandas_ta as ta
import time

pair = 'BCHUSDT'
time_frame = '1m'
pair_num = 0
candle_limit = 201
SMA_window = 36
EMA_window = 200
ATR_window = 5
CCI_window = 50
ST_window = 10
ST_multi = 3.0
ST_window2 = 20
ST_multi2 = 4.2
MACD_fast = 12
MACD_slow = 26
MACD_signal = 9
df = ''
df_i = ''
max_i_w = 0
delta_df = 0
sell_flag = False
buy_flag = False
size = 0.0
pos_amt = 0
sma_angle = 0
sma_angle_limit = 0.5
sma_angle_candles = 20
entry_price = 0
take_price = 0
stop_price = 0
profit_factor = 2
risk = 0.01

exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': config.a_key,
    'secret': config.a_secret,
    'timeout': 30000,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})

pos = exchange.fetch_balance()['info']['positions']  # Читаем позиции по всем доступным парам

print('Баланс USDT: {}'.format(exchange.fetch_balance()['USDT']['total']))# Выводит баланс фьючерсного кошелька в USDT/BUSD/BNB
print('Свободно: {}'.format(exchange.fetch_balance()['USDT']['free']))# 'total' - всего, 'free' - свободно, 'used' - используется
print('Используется: {}'.format(exchange.fetch_balance()['USDT']['used']))
print('-' * 30)
#risk = float(input('Введите риск _> '))

for i in range(len(pos)):  # Находим нужную нам пару в списке pos[n]
    if pos[i]['symbol'] == pair:
        pair_num = i
        print(f'Пара: {pair} (номер: {pair_num})')  # Выводим нужную нам пару и ее номер

    if pair_num == '':
        print(f'Заданный инструмент не найден на бирже {exchange_id}!')  # Сообщаем что пара не найдена


def read_pair_data(pair):  # ЧИТАЕМ ДАННЫЕ ПАРЫ
    global df, delta_df, df_i, max_i_w
    # Создаем датафреймы ------------------------------------------------------------------------
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
    st2 = ta.supertrend(df_i['High'], df_i['Low'], df_i['Close'], ST_window2, ST_multi2)
    df_i['St2'] = st2['SUPERT_' + str(ST_window2) + '_' + str(ST_multi2)]
    df_i['St_d2'] = st2['SUPERTd_' + str(ST_window2) + '_' + str(ST_multi2)]
    # -------------------------------------------------------------------------------------------

    df = df_i[delta_df:]  # Формируем срез и df_i (индикаторный датафрейм)
    df.index = np.arange(len(df))  # Перенумеровали номера свечей начиная с нуля
    return df, df_i


def check_pos(pair_num):
    global buy_flag, sell_flag, pos, df, entry_price, pos_amt
    pos = exchange.fetch_balance()['info']['positions'][pair_num]
    pos_amt = float(pos['positionAmt'])
    if pos_amt == 0:
        exchange.cancelAllOrders(pair)
        sell_flag, buy_flag = False, False

    if pos_amt > 0:
        buy_flag = True
        entry_price = pos['entryPrice']
        print(f'\r ТВХ ▲ {entry_price} Профит: {round(float(pos["unrealizedProfit"]), 2)} угол: {round(sma_angle, 3)}',
              end='', flush=True)

    if pos_amt < 0:
        sell_flag = True
        entry_price = pos['entryPrice']
        print(f'\r ТВХ ▼ {entry_price} Профит: {round(float(pos["unrealizedProfit"]), 2)} угол: {round(sma_angle, 3)}',
              end='', flush=True)

    if profit_factor == 2 and pos_amt != 0:
        ohlcv = exchange.fetch_ohlcv(pair, time_frame)
        price = ohlcv[-1][4]
        if pos_amt > 0:
            if sma_angle < sma_angle_limit - sma_angle_limit * .2:
                exchange.create_order(pair, 'MARKET', 'sell', abs(pos_amt))
                time.sleep(0.2)
                print()
                print(f'Позиция закрыта {str(datetime.now().time())[:8]}')
                pos_amt = float(pos['positionAmt'])

        elif pos_amt < 0:
            if sma_angle < sma_angle_limit - sma_angle_limit * .2:
                exchange.create_order(pair, 'MARKET', 'buy', abs(pos_amt))
                time.sleep(0.2)
                print()
                print(f'Позиция закрыта {str(datetime.now().time())[:8]}')
                pos_amt = float(pos['positionAmt'])

def strategy():
    global buy_flag, sell_flag, sma_angle, size, df, df_i, entry_price, profit_factor
    last_candle = candle_limit - 1
    sma_angle = max(df_i['Sma'][-sma_angle_candles:]) - min(df_i['Sma'][-sma_angle_candles:])
    sma_direct = None
    if float(pos['positionAmt']) == 0:
        print(f'\r Угол: {round(sma_angle,5)} за {sma_angle_candles} свечей, порог: {round(sma_angle_limit, 4)} ', end='', flush=True)
    sma = df['Sma'][last_candle]
    old_sma = df['Sma'][last_candle-1]
    macd = df['Macd'][last_candle]
    macd_h = df['Macd_h'][last_candle]
    macd_s = df['Macd_s'][last_candle]
    entry_price = df['Close'][last_candle]
    st_d = df['St_d'][last_candle]
    price = df['Close'][last_candle]
    stop_price = df['St'][last_candle]

    if sma > old_sma:
        sma_direct = 1
    else:
        sma_direct = -1

    # ПОКУПКИ / ПРОДАЖИ
    if not sell_flag and not buy_flag:  # Проверяем состояние флагов позиций
        # проверяем условия покупки инструмента
        if sma_angle > sma_angle_limit and sma_direct == 1:
            profit_factor = 2
            check_pos(pair_num)
            free_balance = float(exchange.fetch_balance()['USDT']['free'])
            size = free_balance * risk
            print()
            print(str(datetime.now().time())[:8])
            print(f'Точка входа {round(entry_price, 6)}')
            print(f'Размер позиции {round(size, 6)}')
            print('Покупаем ↑ ↑ ↑')
            open_buy_market_order(pair, size)

        # проверяем условия продажи инструмента
        if sma_angle > sma_angle_limit and sma_direct == -1:
            profit_factor = 2
            check_pos(pair_num)
            free_balance = float(exchange.fetch_balance()['USDT']['free'])
            size = free_balance * risk
            print()
            print(str(datetime.now().time())[:8])
            print(f'Точка входа {round(float(entry_price), 6)}')
            print(f'Размер позиции {round(size, 6)}')
            print('Продаем ↓ ↓ ↓')
            open_sell_market_order(pair, size)

def open_buy_market_order(pair, size):
    global buy_flag
    try:
        order = exchange.create_order(pair, 'MARKET', 'buy', size)
        print(str(datetime.now().time())[:8])
        print(f'Позиция BUY {pair} успешно открыта')

        buy_flag = True
        return True

    except Exception as e:
        exchange.cancelAllOrders(pair)
        print(str(datetime.now().time())[:8])
        print('Не удалось открыть позицию на покупку!')
        print(f'Ошибка: {format(e)}')
        buy_flag = False
        return False


def open_sell_market_order(pair, size):
    global sell_flag
    try:
        order = exchange.create_order(pair, 'MARKET', 'sell', size)
        print(str(datetime.now().time())[:8])
        print(f'Позиция SELL {pair} успешно открыта')
        sell_flag = True
        return True

    except Exception as e:
        exchange.cancelAllOrders(pair)
        print(str(datetime.now().time())[:8])
        print('Не удалось открыть позицию на продажу!')
        print(f'Ошибка: {format(e)}')
        sell_flag = False
        return False


old_time = str(datetime.now().time())
read_pair_data(pair=pair)
check_pos(pair_num)

while True:
    current_time = str(datetime.now().time())
    if current_time[4] != old_time[4]:  # Читаем данные инструмента каждую минуту
        read_pair_data(pair=pair)
        old_time = current_time
        strategy()
    check_pos(pair_num)

