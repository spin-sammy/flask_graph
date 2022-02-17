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
SMA_window = 21
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
ema_angle = 0
ema_angle_limit = 0.3
ema_angle_candles = 20
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
        print(f'\r ТВХ ▲ {entry_price} Профит: {round(float(pos["unrealizedProfit"]), 2)}', end='', flush=True)
        #print(f'Точка входа в покупки ▲ {entry_price}')
        #print(f'Профит: {pos["unrealizedProfit"]}')

    if pos_amt < 0:
        sell_flag = True
        entry_price = pos['entryPrice']
        print(f'\r ТВХ ▼ {entry_price} Профит: {round(float(pos["unrealizedProfit"]), 2)}', end='', flush=True)
        #print(f'Точка входа в продажи ▼ {entry_price}')
        #print(f'Профит: {pos["unrealizedProfit"]}')

    if profit_factor == 2 and pos_amt != 0:
        ohlcv = exchange.fetch_ohlcv(pair, time_frame)
        price = ohlcv[-1][4]
        if pos_amt > 0 and int(df['St_d2'][candle_limit-1]) == 1:
            if price <= float(df['St2'][candle_limit-1]):
                exchange.create_order(pair, 'MARKET', 'sell', abs(pos_amt))
                time.sleep(0.2)
                print()
                print(f'Позиция закрыта {str(datetime.now().time())[:8]}')
                pos_amt = float(pos['positionAmt'])

        elif pos_amt < 0 and df['St_d2'][candle_limit-1] == -1:
            if price >= float(df['St2'][candle_limit-1]):
                exchange.create_order(pair, 'MARKET', 'buy', abs(pos_amt))
                time.sleep(0.2)
                print()
                print(f'Позиция закрыта {str(datetime.now().time())[:8]}')
                pos_amt = float(pos['positionAmt'])

def strategy():
    global buy_flag, sell_flag, ema_angle, size, df, df_i, entry_price, stop_price, take_price, profit_factor
    last_candle = candle_limit - 1
    ema_angle = max(df_i['Ema'][-ema_angle_candles:]) - min(df_i['Ema'][-ema_angle_candles:])
    if float(pos['positionAmt']) == 0:
        print(f'\r Угол: {round(ema_angle,5)} за {ema_angle_candles} свечей, порог: {ema_angle_limit} ', end='', flush=True)
    #print(f'Угол наклона (условно): {ema_angle} за {ema_angle_candles} свечей, порог: {ema_angle_limit}')
    ema = df['Ema'][last_candle]
    macd = df['Macd'][last_candle]
    macd_h = df['Macd_h'][last_candle]
    macd_s = df['Macd_s'][last_candle]
    entry_price = df['Close'][last_candle]
    st_d = df['St_d'][last_candle]
    price = df['Close'][last_candle]
    stop_price = df['St'][last_candle]

    # ПОКУПКИ / ПРОДАЖИ
    if not sell_flag and not buy_flag:  # Проверяем состояние флагов позиций
        # проверяем условия покупки инструмента
        if price > ema and ema_angle > ema_angle_limit \
                and macd_h >= df['Macd_h'][last_candle - 1] \
                and st_d == 1:  # Если всё совпало тогда - покупаем!
            profit_factor = 2
            check_pos(pair_num)
            delta_price = abs(entry_price - stop_price)
            take_price = entry_price + (delta_price * profit_factor)
            free_balance = float(exchange.fetch_balance()['USDT']['free'])
            size = (free_balance * risk) / delta_price
            print(str(datetime.now().time())[:8])
            print(f'Точка входа {round(entry_price, 6)}')
            print(f'Стоп-лосс {round(stop_price, 6)}')
            print(f'Тейк-профит {round(take_price, 6)}')
            print(f'Размер позиции {round(size, 6)}')
            print('Покупаем! Без нулевой линии!')
            open_buy_market_order(pair, size, stop_price, take_price)

        # проверяем условия продажи инструмента
        if price < ema and ema_angle > ema_angle_limit \
                and macd_h <= df['Macd_h'][last_candle - 1] \
                and st_d == -1:  # Если всё совпало тогда - продаем!
            profit_factor = 2
            check_pos(pair_num)
            delta_price = abs(entry_price - stop_price)
            take_price = entry_price - (delta_price * profit_factor)
            free_balance = float(exchange.fetch_balance()['USDT']['free'])
            size = (free_balance * risk) / delta_price
            print(str(datetime.now().time())[:8])
            print(f'Точка входа {round(float(entry_price), 6)}')
            print(f'Стоп-лосс {round(float(stop_price), 6)}')
            print(f'Тейк-профит {round(float(take_price), 6)}')
            print(f'Размер позиции {round(size, 6)}')
            print('Продаем ! Без нулевой линии!')
            open_sell_market_order(pair, size, stop_price, take_price)

def open_buy_market_order(pair, size, stop_price, take_price):
    global buy_flag
    try:
        stopLossParams = {'closePosition': True, 'stopPrice': stop_price, 'reduce_only': True}
        stop_order = exchange.create_order(pair, 'STOP_MARKET', 'sell', size, None, stopLossParams)
        print(f'Успешно установлен стоп-ордер {round(stop_price, 6)} ')

        takeProfitParams = {'closePosition': True, 'stopPrice': take_price, 'reduce_only': True}
        take_order = exchange.create_order(pair, 'TAKE_PROFIT_MARKET', 'sell', size, None, takeProfitParams)
        print(f'Успешно установлен тейк-профит {take_price}.')

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


def open_sell_market_order(pair, size, stop_price, take_price):
    global sell_flag
    try:
        stopLossParams = {'closePosition': True, 'stopPrice': stop_price, 'reduce_only': True}
        stop_order = exchange.create_order(pair, 'STOP_MARKET', 'buy', size, None, stopLossParams)
        print(f'Успешно установлен стоп-ордер {round(stop_price, 6)}')

        takeProfitParams = {'closePosition': True, 'stopPrice': take_price, 'reduce_only': True}
        take_order = exchange.create_order(pair, 'TAKE_PROFIT_MARKET', 'buy', size, None, takeProfitParams)
        print(f'Успешно установлен тейк-профит {take_price}.')

        order = exchange.create_order(pair, 'MARKET', 'sell', size)
        print(str(datetime.now().time())[:8])
        print(f'Позиция SELL {pair} успешно открыта')
        #print(order)
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
    t = int(current_time[:2])
    if t >= 4 and t <= 22:
        if current_time[4] != old_time[4]:  # Читаем данные инструмента каждую минуту
            read_pair_data(pair=pair)
            old_time = current_time
            strategy()
        check_pos(pair_num)
        #print(f'sell_flag = {sell_flag}, buy_flag = {buy_flag}')
