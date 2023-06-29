import sqlite3
import json
import time as tm
import datetime
import numpy as np
import csv
import matplotlib.pyplot as plt
import pandas as pd
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
import numpy as np


class Data:
    def __init__(self, heart_data, steps_data, timestamps):
        self.heart = heart_data
        self.steps = steps_data
        self.timestamps = timestamps

    def get_steps(self, timestamp):
        if timestamp in self.timestamps:
            index = self.timestamps.index(timestamp)
            return self.steps[index]
        else:
            return None
        
    def get_heartrate(self, timestamp):
        if timestamp in self.timestamps:
            index = self.timestamps.index(timestamp)
            return self.heart[index]
        else:
            return None
        
    def get_date(self, timestamp):
        if timestamp in self.timestamps:
            time = datetime.datetime.utcfromtimestamp(timestamp).isoformat()
            return time[0:10]
        else:
            return None
        
    def get_utc_time(self, timestamp):
        if timestamp in self.timestamps:
            time = datetime.datetime.utcfromtimestamp(timestamp).isoformat()
            return time
        else:
            return None

def daily_summary(steps, heart, date):
    with open("./data/daily.csv", "a", newline="") as f:
        writer = csv.writer(f)
        # verify row
        try:
            df = pd.read_csv("./data/daily.csv")
            if df.empty:
                writer.writerow(("Date", "Steps", "Heart"))
        except:
            writer.writerow(("Date", "Steps", "Heart"))
        writer.writerow((date, sum(steps), np.average(heart)))

def main_read(cursor):
    rows = cursor.fetchall()
    i = int()
    data = dict()
    heart = int()
    heart_list, steps_list = list(), list()
    date_prev = str()
    for row in rows:
        time_stamp = row[0]
        steps = row[4]
        if row[6] > 10 and row[6] < 250:
            heart = True
        else:
            heart = False
        if row[4] > 0:
            steps = True
        else:
            steps = False
        if steps or heart:
            human_time = datetime.datetime.utcfromtimestamp(time_stamp).isoformat()
            data[i] = {}
            data[i]["unix_time"] = time_stamp
            data[i]["human_time"] = human_time
            if steps:
                data[i]["steps"] = row[4]
            if heart:
                data[i]["heart"] = row[6]
            i += 1
            date = human_time[0:10]
            heart_list.append(row[6])
            steps_list.append(row[4])
            if date_prev != date and i > 10:
                daily_summary(steps_list, heart_list, date)
                heart_list = []
                steps_list = []
            date_prev = date
    with open("./data/data.json", "w") as f:
        json.dump(data, f, indent=4)

def data_read(cursor):
    rows = cursor.fetchall()
    i = int()
    data = dict()
    heart = int()
    heart_list, steps_list, time_list, unix_list = list(), list(), list(), list()
    date_prev = str()
    for row in rows:
        time_stamp = row[0]
        steps = row[4]
        if row[6] > 10 and row[6] < 250:
            heart = True
        else:
            heart = False
        if row[4] > 0:
            steps = True
        else:
            steps = False
        if steps or heart:
            human_time = datetime.datetime.utcfromtimestamp(time_stamp).isoformat()
            data[i] = {}
            data[i]["unix_time"] = time_stamp
            data[i]["human_time"] = human_time
            if steps:
                data[i]["steps"] = row[4]
                steps_list.append(row[4])
            else:
                steps_list.append(None)
            if heart:
                data[i]["heart"] = row[6]
                heart_list.append(row[6])
            else:
                heart_list.append(None)
            i += 1
            date = human_time[0:10]
            time_list.append(human_time)
            unix_list.append(time_stamp)
            date_prev = date
    return steps_list, heart_list, time_list, unix_list

def csv_write():
    time_stamps = data.timestamps
    with open("./data/data.csv", "a", newline='') as f:
        writer = csv.writer(f)
        if f.tell() == 0:  # Check if the file is empty
            writer.writerow(("Time", "Heart", "Steps"))  # Write the header if the file is empty
        for item in time_stamps:
            time = data.get_utc_time(item)
            heart = data.get_heartrate(item)
            steps = data.get_steps(item)
            writer.writerow((time, heart, steps))

def init():
    global cursor
    conn = sqlite3.connect("./export/data.db")
    cursor = conn.cursor()
    table_name = 'MI_BAND_ACTIVITY_SAMPLE'
    cursor.execute(f'SELECT * FROM {table_name}')
    steps_list, heart_list, time_list, unix_list = data_read(cursor)
    data = Data(heart_list, steps_list, unix_list)
    return data

def calculate_pai_score(heart_rate_data):
    c1 = 10.1817
    c2 = 5.7808
    c3 = 41.9374
    c4 = 9.8382
    ymax = 199
    yth = 80
    time_period = 358860
    heart_rate_data = [x for x in heart_rate_data if x is not None]
    print(heart_rate_data)
    heart_rate_data = np.array(heart_rate_data)
    normalized_intensity = (heart_rate_data - yth)/(ymax - yth)
    intensity_score = c1 * (np.exp(c2*normalized_intensity)-1)
    activity_score = -time_period * np.trapz(intensity_score)
    pai_score = c3 + c4 * (1 - np.exp(activity_score))
    mi_band_coefficient = 116/51.7756 # this was my coefficient for V to PAI conversion, your mileage may differ
    pai_score = pai_score * mi_band_coefficient
    return pai_score


def heart_rate_plot(csv_path = ""):

    plt.figure(figsize=(12, 6))
    plt.subplots_adjust(left=0.1, right=0.95, bottom=0.2, top=0.9)

    if csv_path != "":
        with open(csv_path, "r") as f:
            reader = csv.reader(f)
            next(reader)
            time, heart = list(), list()
            for row in reader:
                time.append(row[0])
                heart.append(row[1])
    else:
        heart = data.heart
        time = list()
        time_stamps = data.timestamps

        for item in time_stamps:  
            time.append(data.get_utc_time(item))

    x_points = data.timestamps
    y_points = heart

    def main(data):
        data_smooth = list()
        for i in range(len(data)):
            def main(data, i):
                sum, runs = int(), 0
                for subcount in range(9):
                    try:
                        sum += int(data[i-5+subcount])
                        runs += 1
                    except:
                        pass
                    subcount += 1
                point_smooth = sum/runs if runs > 0 else None
                return point_smooth
            data_smooth.append(round(main(data, i)))
            i += 1
        return data_smooth
    
    y_points_smooth = main(y_points)
    y_points_smooth = savgol_filter(y_points_smooth, 21, 2)
    x_points = x_points[0:-1]
    y_points_smooth = y_points_smooth[0:-1]
    
    def get_ticks():
        points = x_points[::round((len(x_points)/10))]
        date = list()
        for item in points:
            date.append(data.get_utc_time(item))
        return date
    
    x_labels = get_ticks()

    plt.xticks(x_points[::round((len(x_points)/10))], x_labels, rotation=45)
    plt.ylim(60, 200)
    plt.xlim(x_points[0], x_points[-1])
    plt.plot(x_points, y_points_smooth)

    plt.savefig("./data/figure.png", dpi = 400)
    plt.show()

    tm.sleep(10)

global data
data = init()
print(calculate_pai_score(data.heart))

