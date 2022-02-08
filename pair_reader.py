import ccxt
from datetime import datetime
import pandas as pd
import os, sys, config
from time import gmtime, strftime
from ta.trend import SMAIndicator, EMAIndicator
from ta.volatility import AverageTrueRange
import matplotlib.animation as animation
import matplotlib.pyplot as plt

root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root + '/python')
exchange_id = 'binance'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey' : config.a_key,
    'secret' : config.a_secret,
    'timeout' : 30000,
    'enableRateLimit' : True,
    'options' : {'defaultType' : 'future'},
    })
pair_symbol = input('Какую криптовалюту читаем? _ ') + '/USDT'
print('Таймфреймы:')
print('1m - одна минуты, 5m - 5 минут и тд...')
print('1h - один час, 4h - 4 часа и тд...')
print('1d - один день')
time_frame = input('Какой таймфрейм читаем? _ ')
bar_limit = int(input('Сколько баров читаем? _ '))

#pair_symbol = input('Какую пару читаем? ')
pair_symbol = pair_symbol.upper()
#pair_file_name = input('Файл для сохранения {} + '.format(pair_symbol))
pair_file_name = strftime("%d%m_%H%M", gmtime()) +'_'+ str(bar_limit) + '_' + time_frame
print(pair_symbol)
# Создаем датафрейм -------------------------------------------------------------------------
bars = exchange.fetch_ohlcv(pair_symbol, limit=bar_limit, timeframe=time_frame)   # Выводит limit минутных свечей
df = pd.DataFrame(bars, columns=['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume'])
# Заменяем timestamp на время UTC в датафрейме df[] -----------------------------------------
df['Datetime'] = [datetime.fromtimestamp(x/1000) for x in df['Datetime']]
# Индикатор тренда SMA ----------------------------------------------------------------------
sma_indicator = SMAIndicator(df['Close'], window=21)
df['Sma'] = sma_indicator.sma_indicator()
# -------------------------------------------------------------------------------------------
# Индикатор тренда EMA ----------------------------------------------------------------------
ema_indicator =EMAIndicator(df['Close'], window=21)
df['Ema'] = ema_indicator.ema_indicator()
# -------------------------------------------------------------------------------------------

# Индикатор волатильности ATR ---------------------------------------------------------------
atr_indicator = AverageTrueRange(df['High'], df['Low'], df['Close'], window = 21)
df['Atr'] = atr_indicator.average_true_range()
# -------------------------------------------------------------------------------------------
df.to_csv(('./static/' + pair_symbol.replace('/USDT', '-USDT')) + '_' + pair_file_name + '.csv', index= False)
print(df)



fig = plt.figure()
ax = plt.axes(xlim = (min(df.index), max(df.index)), ylim =(min(df['Close']), max(df['Close'])))
line, = ax.plot([], [], lw=2)
def init():
    line.set_data([], [])
    return line,
xdata, ydata = [], []

def animate(i):
    x = i
    y = df['Close'][i]
    xdata.append(x)
    ydata.append(y)
    line.set_data(xdata, ydata)
    return line,

anim = animation.FuncAnimation(fig, animate, init_func= init, interval=5, blit=True)
#anim.save('ETH-USDT.gif', dpi=150, fps=30, writer='pillow')
plt.show()
