from flask import Flask, render_template, request
import pandas as pd
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from statistics import mean


app = Flask(__name__)
all_points = {}
levels = []
pair_file_name = 'None'



def take_levels(df):
    count = 0
    bar_count = 0
    average_volume = mean(df['Volume'][-10:-1])
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
    average_value = mean(min_4_values)
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

@app.route('/', methods=['POST', 'GET'])
def index():
    global chars_round, touches, volume_divider

    if request.method == 'POST':
        pair_file_name = request.form['file_name']
        chars_round = int(request.form['round_control'])
        touches = int(request.form['touches'])
        volume_divider = int(request.form['volume_divider'])
        print('файл = ' + pair_file_name)
        print('сколько знаков округлять = ' + str(chars_round))
        print('количество касаний = ' + str(touches))
        print('делитель объема = ' + str(volume_divider))
        # ====================================================
        # Читаем данные из файла
        df = pd.read_csv('./static/' + pair_file_name)
        # ====================================================
        candle_limit = len(df.index)
        plt.style.use('mpl20')
        plt.figure(figsize=(16, 8), clear=True)
        ax1 = plt.subplot2grid((4, 2), (0, 0), colspan=2, rowspan=3)
        plt.setp(ax1.get_xticklabels(), visible=False)
        # Вычисляем уровни
        take_levels(df)

        # Выводим уровни
        for i in levels:
            ax1.text(-5, float(i), str(round(i, 4)), backgroundcolor='w', fontsize=6)
            ax1.axhline(float(i), color='g', linestyle='-', linewidth=1)  # отрисовка уровня
        levels.clear()
        # Отрисовываем бары и машку
        for n in range(candle_limit - 1):
            # ax1.vlines(x=n, ymin=df['Low'][n], ymax=df['High'][n], colors='mediumblue', linewidth=1.2)
            ax1.vlines(x=n, ymin=df['Low'][n], ymax=df['High'][n], color='mediumblue', linewidth=1.0)
            if df['Close'][n] > df['Open'][n]:
                ax1.vlines(x=n, ymin=df['Close'][n], ymax=df['Open'][n], colors='g',
                           linewidth=4)  # Подсветка бара с большим обьемом
            else:
                ax1.vlines(x=n, ymin=df['Close'][n], ymax=df['Open'][n], colors='r',
                           linewidth=4)  # Подсветка бара с большим обьемом

        # Выводим подписи к осям и сетку
        plt.grid(True, 'major')
        plt.title('файл: ' + pair_file_name)
        plt.ylabel('цена (USDT)')
        ax2 = plt.subplot2grid((4, 2), (3, 0), colspan=2, rowspan=2, sharex=ax1)
        plt.bar(df.index, df['Volume'])
        plt.grid(True, 'major')
        plt.subplots_adjust(left=.05, right=.98, bottom=0.05, top=.96, hspace=0)
        # make these tick labels invisible
        plt.savefig('./static/images/chart.png')
        plt.cla()
        plt.clf()
        plt.close()
        # plt.show()
        return render_template('index.html', chart_name='chart.png',\
                               file_name=pair_file_name,\
                               round_control=chars_round, touches=touches,\
                               volume_divider=volume_divider)
    else:
        chart_name = 'empty.png'
        levels.clear()
        return render_template('index.html', chart_name='empty.png')


if __name__ == '__main__':
    app.run()
