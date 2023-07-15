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
import drive
from utils import get_config
import pytz


class Data:
    def __init__(self, timestamps, heart_data=[], steps_data=[], activity_data=[]):
        self.heart = heart_data
        self.steps = steps_data
        self.timestamps = timestamps
        self.activity = self.Activity(activity_data, timestamps)

    class Activity:
        def __init__(self, data, timestamps):
            self.raw = data
            self.type = self.get_type(data)
            self.timestamps = timestamps

        def get_type(self, data):
            result = []
            prefix = "./activity_type/"
            activity_config_file = prefix + get_config()["device"].lower().replace(" ", "_") + ".json"
            with open(activity_config_file) as f:
                activity_config = json.load(f)
                activity_config = {value: key for key, value in activity_config.items()} # using inverted dict for easier search
            for item in data:
                result.append(activity_config[item]) if item in activity_config else result.append(None)
            return result
        
        def get_activity_id(self, timestamp):
            if timestamp in self.timestamps:
                index = self.timestamps.index(timestamp)
                return self.raw[index]
            else:
                return None
    
        def get_activity_type(self, timestamp):
            if timestamp in self.timestamps:
                index = self.timestamps.index(timestamp)
                return self.type[index]
            else:
                return None
            
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
        
    def get_local_time(self, timestamp):
        if timestamp in self.timestamps:
            # Convert Unix timestamp to datetime object
            dt = datetime.datetime.fromtimestamp(timestamp)

            # Get the local time zone
            local_timezone = pytz.timezone('Europe/Prague')

            # Convert datetime object to local time
            local_time = dt.astimezone(local_timezone).strftime('%Y-%m-%dT%H:%M:%S')

            return local_time
        else:
            return None
        
    def get_timestamp(self, date):
        # supports either date or time specifically (for ease of use)
        if len(date) == 10:
            time = datetime.datetime.strptime(date, '%Y-%m-%d')
        else:
            time = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')

        timestamp = (time - datetime.datetime(1970, 1, 1)).total_seconds()
        if timestamp not in self.timestamps:
            print("WARNING: Timestamp provided is not in Data object, function will default to the closest one.")
            if timestamp > max(self.timestamps):
                timestamp = max(self.timestamps)
            elif timestamp < min(self.timestamps):
                timestamp = min(self.timestamps)
            else:
                raise ValueError("When handling this exception an error occured.")
        return timestamp
        
    def get_midnight(self, zone="00:00:00"): # Set the UTC time which should be marked as midnight (22:00:00 for CEST)
        midnights, days = list(), list()
        for item in self.timestamps:
            if self.get_utc_time(item).endswith(zone):
                midnights.append(item)
                correction_time = 86400 - (int(zone[0:2])*60*60) # There needs to be correction so that it's local time
                days.append(self.get_date(item+correction_time))
        return midnights, days # Returns the UNIX times for midnights and returns which days those are
    
    def range(self, start_time, end_time):
        filtered_heart = []
        filtered_steps = []
        filtered_timestamps = []
        filtered_activity = []
    
        for i in range(len(self.timestamps)):
            timestamp = self.timestamps[i]
            if start_time <= timestamp <= end_time:
                filtered_heart.append(self.heart[i])
                filtered_steps.append(self.steps[i])
                filtered_timestamps.append(timestamp)
                filtered_activity.append(self.activity[i])
        
        return Data(heart_data=filtered_heart, steps_data=filtered_steps, timestamps=filtered_timestamps, activity_data=filtered_activity)

def daily_summary(data):
    steps_list, heart_list = list(), list()
    timestamps, datums = data.get_midnight("22:00:00")

    for index in range(len(timestamps)):
        bottom_limit = timestamps[index]
        upper_limit = timestamps[index+1] if index+1 < len(timestamps) else max(data.timestamps)
        filtered_data = data.range(bottom_limit, upper_limit)
        print(filtered_data)
        final_data = [item for item in filtered_data.steps if item is not None]
        final_data = sum(final_data)
        steps_list.append(final_data)

    for index in range(len(timestamps)):
        bottom_limit = timestamps[index]
        upper_limit = timestamps[index+1] if index+1 < len(timestamps) else max(data.timestamps)
        filtered_data = data.range(bottom_limit, upper_limit)
        print(filtered_data)
        final_data = [item for item in filtered_data.steps if item is not None]
        final_data = round(np.average(final_data))
        heart_list.append(final_data)

    with open("./data/daily.csv", "a", newline="") as f:
        writer = csv.writer(f)
        # verify row
        try:
            df = pd.read_csv("./data/daily.csv")
            if df.empty:
                writer.writerow(("Date", "Steps", "Heart"))
        except:
            writer.writerow(("Date", "Steps", "Heart"))
        writer.writerows(zip(datums, steps_list, heart_list))

def data_read(cursor):
    # fetch sqlite
    rows = cursor.fetchall()

    # variable initilialisation
    heart_list, steps_list, time_list, unix_list, activity_list = list(), list(), list(), list(), list()

    # new reader (2023-07-02)
    for row in rows:
        # read data from sheet
        time_stamp, steps, heart, activity = int(), int(), int(), int()
        time_stamp, steps, heart, activity = row[0], row[4], row[6], row[5]

        # append data
        time_list.append(datetime.datetime.utcfromtimestamp(time_stamp).isoformat())
        unix_list.append(time_stamp)
        steps_list.append(steps) if steps > 0 else steps_list.append(None)
        heart_list.append(heart) if 250 > heart > 10 else heart_list.append(None)
        activity_list.append(activity)

    return steps_list, heart_list, time_list, unix_list, activity_list

def csv_write(data):
    time_stamps = data.timestamps
    with open("./data/data.csv", "a", newline='') as f:
        writer = csv.writer(f)
        if f.tell() == 0:  # Check if the file is empty
            writer.writerow(("Time", "Heart", "Steps"))  # Write the header if the file is empty
        for item in time_stamps:
            time = data.get_local_time(item)
            heart = data.get_heartrate(item)
            steps = data.get_steps(item)
            activity_id = data.activity.get_activity_id(item)
            activity_type = data.activity.get_activity_type(item)
            writer.writerow((time, heart, steps, activity_id, activity_type))

def init(location):
    # the function can read from CSV, JSON and SQLITE DB files automatically
    # filetype does not need to be specified, only the location (can be relative)
    location_type = location.split(".")[-1]

    if location_type == "db":
        global cursor
        conn = sqlite3.connect(location)
        cursor = conn.cursor()
        if get_config()["device"] == "Amazfit Band 5":
            table_name = 'MI_BAND_ACTIVITY_SAMPLE'
        elif get_config()["device"] == "Mi Band 7":
            table_name = 'HUAMI_EXTENDED_ACTIVITY_SAMPLE'
        cursor.execute(f'SELECT * FROM {table_name}')
        steps_list, heart_list, time_list, unix_list, activity_list = data_read(cursor)

    elif location_type == "csv":
        with open(location, "r") as f:
            reader = csv.reader(f)
            next(reader)
            steps_list, heart_list, unix_list = list(), list(), list()
            for row in reader:
                steps_list.append(int(row[2])) if row[2] != "" else steps_list.append(None)
                heart_list.append(int(row[1])) if row[1] != "" else heart_list.append(None)
                time_meta = datetime.datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S")
                unix_list.append(int(datetime.datetime.timestamp(time_meta)))

    elif location_type == "json":
        with open(location, "r") as f:
            data = json.load(f)
            supported_items = data[str(0)].keys()
            steps_list, heart_list, unix_list = list(), list(), list()
            for i in range(len(data)):
                heart_list.append(data[str(i)].get("heart", None) if "heart" in supported_items else None)
                unix_list.append(data[str(i)].get("unix_time", None) if "unix_time" in supported_items else None)
                steps_list.append(data[str(i)].get("steps", None) if "steps" in supported_items else None)


    data = Data(timestamps=unix_list, steps_data=steps_list, heart_data=heart_list, activity_data=activity_list)
    return data

def calculate_pai_score(heart_rate_data):
    c1 = 10.1817
    c2 = 5.7808
    c3 = 41.9374
    c4 = 9.8382
    ymax = 199
    yth = 80
    time_period = 60*60*24*7
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


def heart_rate_plot(data, offset=10, figsize=(12,6), save=True, dpi=400, zone="22:00:00"):

    plt.figure(figsize=figsize)

    x_points = data.timestamps
    y_points = data.heart

    def correct_nones(data):
        current_data,data_smooth, i = list(), list(), int()
        for item in data:
            i += 1
            current_data.append(item)
            if len(current_data) > 10: current_data.pop(0)
            rounding_list = [value for value in current_data if value is not None]
            if not rounding_list: 
                try:
                    data_smooth.append(round(np.average(data_smooth[i-5:i+5])))
                except:
                    index_of_first = i
                    for item in data:
                        if data[index_of_first]: 
                            result = data[index_of_first]
                            break
                        else:
                            index_of_first += 1
                    data_smooth.append(result)
            else: data_smooth.append(round(np.average(rounding_list)))
        return data_smooth
    
    y_points_smooth = correct_nones(y_points)
    y_points_smooth = savgol_filter(y_points_smooth, 21, 2)
    x_points = x_points[0:-1]
    y_points_smooth = y_points_smooth[0:-1]

    plt.xticks(*data.get_midnight(zone=zone), ha='left')
    plt.ylim(round(min(y_points_smooth)-offset), round(max(y_points_smooth)+offset))
    plt.xlim(x_points[0], x_points[-1])
    plt.plot(x_points, y_points_smooth)
    plt.savefig("./data/figure.png", dpi=dpi) if save else None
    plt.show()

    tm.sleep(10)

# initialisation from config.json file
if get_config()["update_local_db"]:
    data = init(drive.get_folder(get_config()["data_folder_id"], api_key= get_config()["api_key"]))
else:
    data = init("data.db")

heart_rate_plot(data)

# as of 2023-07-02 data is no longer global (hence you can get specific ranges using the inbuild data.range())
# heart_rate_plot(data.range(data.get_timestamp("2023-06-27"), data.get_timestamp("2023-06-30")))
# please note that the above method will use UTC time so there will be overflow, if you want to avoid it you can specify the time directly ("2023-06-27T22:00:00")
