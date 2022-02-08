import numpy as np
from flask import Flask, render_template, request
import ccxt
from datetime import datetime, time
import pandas as pd
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import config
import pandas_ta as ta

app = Flask(__name__)
all_points = {}
levels = []
# pair_file_name = 'None'
pair = 'BTCUSDT'
time_frame = '1h'
candle_limit = 200
chars_round = 2
touches = 1
volume_divider = 1
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

pairs = config.pairs
tf = config.tf
df = ''


exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': config.a_key,
    'secret': config.a_secret,
    'timeout': 30000,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'},
})


# print('Баланс в USDT: {}'.format(exchange.fetch_balance()['USDT']['total']))# Выводит баланс фьючерсного кошелька в USDT/BUSD/BNB
# print('Свободно: {}'.format(exchange.fetch_balance()['USDT']['free']))# 'total' - всего, 'free' - свободно, 'used' - используется
# print('Используется: {}'.format(exchange.fetch_balance()['USDT']['used']))


def take_levels():
    count = 0
    bar_count = 0
    average_volume = sum(df['Volume'][-10:-1]) / 10
    for point in df['High']:

        for i in df['High']:  # Вычисляем хаи

            if round(point, chars_round) == round(i, chars_round) \
                    and df['Volume'][bar_count] > average_volume / volume_divider:
                count += 1
                print(f'По цене {round(point, chars_round)} есть совпадение по хаям!')
                print('Счетчик: ' + str(count))
            bar_count += 1
        bar_count = 0

        for i in df['Low']:  # Вычисляем лои

            if round(point, chars_round) == round(i, chars_round) \
                    and df['Volume'][bar_count] > average_volume / volume_divider:
                count += 1
                print(f'По цене {round(point, chars_round)} есть совпадение по лоям!')
                print('Счетчик: ' + str(count))
            bar_count += 1
        bar_count = 0

        if count > 1:  # количество касаний одинаковой цены
            all_points[point] = count
        count = 0
    bar_count = 0
    print(len(all_points))
    sorted_all_points = sorted(all_points)  # сортируем по возрастанию
    print(sorted_all_points)
    delta = {}

    for i in range(len(sorted_all_points)):  # строим диапазоны цены (лоёв и хаёв)

        if i > 1:  # если прочитали больше двух цен
            delta[str(sorted_all_points[i]) + '-' + str(sorted_all_points[i - 1])] = round(
                sorted_all_points[i] - sorted_all_points[i - 1], chars_round)
    print(len(delta))
    print(delta)

    min_4_values = sorted(delta.values())[0:5]
    average_value = sum(min_4_values) / 4
    print('abracadabra --> ' + str(average_value))

    for i in delta:  # Шаг цены
        if delta[i] <= average_value:
            print(delta[i])
            levels.append((float(i.split('-')[0]) + float(i.split('-')[1])) / 2)
    delta.clear()
    average_value = 0
    min_4_values = 0
    all_points.clear()
    sorted_all_points.clear()
    print(len(levels))
    print(levels)


def read_pair_data(pair):  # ЧИТАЕМ ДАННЫЕ ПАРЫ
    global df, delta_df

    # Создаем датафрейм -------------------------------------------------------------------------
    max_i_w = max(SMA_window, EMA_window, ATR_window, CCI_window)
    bars_i = exchange.fetch_ohlcv(pair, timeframe=time_frame,
                                  limit=candle_limit + max_i_w)  # Выводит limit минутных свечей
    bars = exchange.fetch_ohlcv(pair, timeframe=time_frame, limit=candle_limit)  # Выводит limit минутных свечей
    df_i = pd.DataFrame(bars_i, columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df = pd.DataFrame(bars, columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
    delta_df = len(df_i) - len(df)
    print(bars)
    print(delta_df)
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

    print(macd)
    print(df_i['Macd'])
    print(df_i['Macd_h'])
    print(df_i['Macd_s'])

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
    print(df)


@app.route('/', methods=['POST', 'GET'])
def index():
    global candle_limit, chars_round, touches, volume_divider, time_frame, SMA_window, EMA_window, ATR_window, \
        CCI_window, ST_window, ST_multi, ST_window2, ST_multi2, pair, MACD_fast, MACD_slow, MACD_signal


    if request.method == 'POST':
        pair = request.form['pair_select']
        time_frame = request.form['timeframe_select']
        candle_limit = int(request.form['candle_limit'])
        SMA_window = int(request.form['SMA_window'])
        EMA_window = int(request.form['EMA_window'])
        ATR_window = int(request.form['ATR_window'])
        CCI_window = int(request.form['CCI_window'])
        ST_window = int(request.form['ST_window'])
        ST_multi = float(request.form['ST_multi'])
        ST_window2 = int(request.form['ST_window2'])
        ST_multi2 = float(request.form['ST_multi2'])
        MACD_fast = int(request.form['MACD_fast'])
        MACD_slow = int(request.form['MACD_slow'])
        MACD_signal = int(request.form['MACD_signal'])
        chars_round = int(request.form['round_control'])
        touches = int(request.form['touches'])
        volume_divider = int(request.form['volume_divider'])
        # print('файл = ' + pair_file_name)
        for v in range(len(pairs)):
            if pairs[v] == pair:
                b = pairs[0]
                pairs[0] = pair
                pairs[v] = b
        t = 0
        for t in range(len(tf)):
            if tf[t] == time_frame:
                b = tf[0]
                tf[0] = time_frame
                tf[t] = b

        print('сколько знаков округлять = ' + str(chars_round))
        print('количество касаний = ' + str(touches))
        print('делитель объема = ' + str(volume_divider))
        # ====================================================
        # Читаем данные из файла
        # df = pd.read_csv('./static/' + pair_file_name)
        # ====================================================
        # ====================================================
        # Читаем данные с биржи
        read_pair_data(pair)
        df_st = df['St']
        # ====================================================

        #take_levels()
        print('Это наш ДФ --- ')
        print(df)
        plt.style.use('mpl20')
        plt.figure(figsize=(16, 8), clear=True)
        ax1 = plt.subplot2grid((4, 2), (0, 0), colspan=2, rowspan=3)
        plt.setp(ax1.get_xticklabels(), visible=False)
        # Вычисляем уровни

        # Выводим уровни
        '''for i in levels:
            ax1.text(-8, float(i), str(round(i, 4)), backgroundcolor='w', fontsize=6)
            ax1.axhline(float(i), color='#006262', linestyle='-', linewidth=1)  # отрисовка уровня
        levels.clear()'''

        # Отрисовываем бары и машку
        # определяем ширину свечей
        cw = 5
        if candle_limit > 199:
            cw = 4
        if candle_limit > 599:
            cw = 3
        if candle_limit > 999:
            cw = 2
        sell_flag = False
        buy_flag = False
        for n in range(candle_limit - 1):

            #   рисуем свечи
            ax1.vlines(x=n, ymin=df['Low'][n], ymax=df['High'][n], color='#38464D', linewidth=0.8)
            if df['Close'][n] > df['Open'][n]:
                ax1.vlines(x=n, ymin=df['Close'][n], ymax=df['Open'][n], colors='g', linewidth=cw)
            else:
                ax1.vlines(x=n, ymin=df['Close'][n], ymax=df['Open'][n], colors='r', linewidth=cw)

            #   стратегия !!!!!!!!!!!!!!!!!!!!!!!!!!
            if df['Close'][n] > df['Sma'][n] and sell_flag \
                    and df['Open'][n] < df['Close'][n] \
                    and df['Open'][n] < df['Sma'][n]:
                sell_flag = False
                ax1.scatter(n, df['Close'][n], color='darkorange')

            if df['Close'][n] < df['Sma'][n] and buy_flag \
                    and df['Open'][n] > df['Close'][n] \
                    and df['Open'][n] > df['Sma'][n]:
                buy_flag = False
                ax1.scatter(n, df['Close'][n], color='darkorange')

            if df['Close'][n] > df['Ema'][n] and buy_flag==False: # buy
                if n >= 1 and df['Macd'][n] < 0 and \
                        df['Macd_s'][n] < 0 and \
                        df['Macd'][n] > df['Macd_s'][n] and \
                        df['Macd_h'][n] >= 0 and \
                        df['St_d'][n] > 0:
                    ax1.scatter(n, df['Close'][n], color='darkblue')
                    ax1.text(-8, float(df['Close'][n]), str(round(df['Close'][n], 4)), backgroundcolor='w', fontsize=6)
                    ax1.axhline(float(df['Close'][n]), color='green', linestyle='-', linewidth=0.6)  # отрисовка уровня
                    ax1.axvline(n, color='#39B255', linestyle='-', linewidth=0.5)  # отрисовка вертикального уровня
                    buy_flag = True


            if df['Close'][n] < df['Ema'][n] and sell_flag==False: # short
                if n >= 1 and df['Macd'][n] > 0 and \
                        df['Macd_s'][n] > 0 and \
                        df['Macd'][n] < df['Macd_s'][n] and \
                        df['Macd_h'][n] <= 0 and \
                        df['St_d'][n] < 0:
                    ax1.scatter(x=n, y=df['Close'][n], color='darkblue')
                    ax1.text(-8, float(df['Close'][n]), str(round(df['Close'][n], 4)), backgroundcolor='w', fontsize=6)
                    ax1.axhline(float(df['Close'][n]), color='red', linestyle='-', linewidth=0.6)  # отрисовка уровня
                    ax1.axvline(n, color='#EB4C42', linestyle='-', linewidth=0.5)  # отрисовка вертикального уровня
                    sell_flag = True

        # Выводим подписи к осям и сетку
        plt.grid(True, 'major')
        plt.title(
            f'пара({time_frame}): {pair}    SMA({SMA_window}): {round(df["Sma"][candle_limit - 1], 4)}    EMA({EMA_window}): {round(df["Ema"][candle_limit - 1], 4)}    ATR({ATR_window}): {round(df["Atr"][candle_limit - 1], 4)}    CCI({CCI_window}): {round(df["Cci"][candle_limit - 1], 4)}    ST: {round(df["St"][candle_limit - 1], 4)}')
        plt.ylabel('цена (USDT)')
        ax2 = plt.subplot2grid((4, 2), (3, 0), colspan=2, rowspan=2, sharex=ax1)
        plt.plot(df.index, df['Macd'], color='red')
        plt.bar(df.index, df['Macd_h'], color='#00C7C7')
        plt.plot(df.index, df['Macd_s'], color='green')
        plt.grid(True, 'major')

        plt.subplots_adjust(left=.05, right=.98, bottom=0.05, top=.96, hspace=0)
        sma_line, = ax1.plot(df.index, df['Sma'], linewidth=1, color='orange')
        ema_line, = ax1.plot(df.index, df['Ema'], linewidth=1, color='darkblue')
        st_line, = ax1.plot(df.index, df['St'], linestyle='--', linewidth=1, color='#FF0000')
        st_line2, = ax1.plot(df.index, df['St2'], linestyle='--', linewidth=1, color='#20BB00')
        ax1.legend((sma_line, ema_line, st_line, st_line2),
                   ['Simple MA', 'Expotential MA', 'Super Trend 1', 'Super Trend 2'])
        plt.legend()
        # make these tick labels invisible

        plt.savefig('./static/images/chart.png', dpi=120)
        plt.cla()
        plt.clf()
        plt.close()
        # plt.show()
        return render_template('index.html', chart_name='chart.png',
                               round_control=chars_round, touches=touches,
                               volume_divider=volume_divider,
                               timeframe_select=time_frame,
                               candle_limit=candle_limit,
                               SMA_window=SMA_window,
                               EMA_window=EMA_window,
                               ATR_window=ATR_window,
                               CCI_window=CCI_window,
                               ST_window=ST_window,
                               ST_multi=ST_multi,
                               ST_window2=ST_window2,
                               ST_multi2=ST_multi2,
                               MACD_fast=MACD_fast,
                               MACD_slow=MACD_slow,
                               MACD_signal=MACD_signal,
                               pairs=pairs, tf=tf)
    else:
        chart_name = 'empty.png'
        levels.clear()
        return render_template('index.html', chart_name='empty.png',
                               round_control=chars_round, touches=touches,
                               volume_divider=volume_divider,
                               timeframe_select=time_frame,
                               candle_limit=candle_limit,
                               SMA_window=SMA_window,
                               EMA_window=EMA_window,
                               ATR_window=ATR_window,
                               CCI_window=CCI_window,
                               ST_window=ST_window,
                               ST_multi=ST_multi,
                               ST_window2=ST_window2,
                               ST_multi2=ST_multi2,
                               MACD_fast=MACD_fast,
                               MACD_slow=MACD_slow,
                               MACD_signal=MACD_signal,
                               pairs=pairs, tf=tf)


if __name__ == '__main__':
    app.run(debug=True)
