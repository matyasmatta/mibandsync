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
from utils import get_config, correct_nones
import pytz
import warnings


class Data:
    def __init__(self, timestamps, heart_data=[], steps_data=[], activity_data=[], sleep_data=[], deep_sleep_data = [], rem_sleep_data = [], whole_sleep_data = []):
        self.heart = heart_data
        self.steps = steps_data
        self.timestamps = timestamps
        self.activity = self.Activity(activity_data, timestamps, sleep_data, deep_sleep_data, rem_sleep_data, whole_sleep_data)

    class Activity:
        def __init__(self, data, timestamps, sleep_data  = [], deep_sleep_data  = [], rem_sleep_data = [], whole_sleep_data = []):
            self.raw = data
            self.type = self.get_type(data)
            self.timestamps = timestamps
            if whole_sleep_data:
                self.sleep = whole_sleep_data
            elif sleep_data:
                self.sleep = self.get_sleep(sleep_data, deep_sleep_data, rem_sleep_data) if sleep_data else []
            else:
                self.sleep = []
                raise Warning("No sleep data provided")
        
        def get_sleep(self, sleep_data, deep_sleep_data, rem_sleep_data):
            result = list()
            for item in self.timestamps:
                metaresult = {}
                index = self.timestamps.index(item)
                metaresult["sleep"] = True if (sleep_data[index] > 20) or (self.raw[index] == "Sleeping") else False
                try:
                    metaresult["deep_sleep"] = True if (deep_sleep_data[index] != 128 and deep_sleep_data[index] > 160) else False
                    metaresult["rem_sleep"] = True if rem_sleep_data[index] > 0 else False
                except:
                    pass
                result.append(metaresult)
            return result

        def get_type(self, data):
            result = []
            prefix = "./activity_type/"
            activity_config_file = prefix + get_config()["device"].lower().replace(" ", "_") + ".json"
            with open(activity_config_file) as f:
                activity_config = json.load(f)
                activity_config = {value: key for key, value in activity_config.items()} # using inverted dict for easier search
            for item in data:
                result.append(activity_config[item]) if item in activity_config else result.append(None)
            if get_config()["fill_activity_data"]: result = correct_nones(result)
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
        
    def get_date(self, timestamp, format = False):
        if timestamp in self.timestamps:
            if format:
                formatted_date = datetime.datetime.utcfromtimestamp(timestamp).strftime("%dth %B")
                return formatted_date
            else:
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
        # Convert Unix timestamp to datetime object
        dt = datetime.datetime.fromtimestamp(timestamp)

        # Get the local time zone
        local_timezone = pytz.timezone('Europe/Prague')

        # Convert datetime object to local time
        local_time = dt.astimezone(local_timezone).strftime('%Y-%m-%dT%H:%M:%S')
        if timestamp in self.timestamps:
            return local_time
        else:
            warnings.warn("Data object function received data not included in self, may cause problems in other functions.", Warning)
            return local_time
        
    def get_timestamp(self, date):
        # supports either date or time specifically (for ease of use)
        if len(date) == 10:
            time = datetime.datetime.strptime(date, '%Y-%m-%d')
        else:
            time = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')

        timestamp = (time - datetime.datetime(1970, 1, 1)).total_seconds()
        if timestamp not in self.timestamps:
            warnings.warn("Timestamp provided is not in Data object, function will default to the closest one.", ImportWarning)
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
        if end_time < start_time:
            raise ValueError("Start time is after end time, code would generate empty Data object.")
        filtered_heart = []
        filtered_steps = []
        filtered_timestamps = []
        filtered_activity = []
        filtered_sleep = []
    
        for i in range(len(self.timestamps)):
            timestamp = self.timestamps[i]
            if start_time <= timestamp <= end_time:
                filtered_heart.append(self.heart[i])
                filtered_steps.append(self.steps[i])
                filtered_timestamps.append(timestamp)
                filtered_activity.append(self.activity.raw[i])
                filtered_sleep.append(self.activity.sleep[i])
        
        return Data(heart_data=filtered_heart, steps_data=filtered_steps, timestamps=filtered_timestamps, activity_data=filtered_activity, whole_sleep_data=filtered_sleep)

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
    timestamp = []
    device_id = []
    user_id = []
    raw_intensity = []
    steps = []
    raw_kind = []
    heart_rate = []
    unknown_1 = []
    sleep = []
    deep_sleep = []
    rem_sleep = []
    utc_time = []

    if get_config()["device"] == "Mi Band 7":
        # new reader (2023-07-02)
        for row in rows:
            # append data
            timestamp.append(row[0])
            device_id.append(row[1])
            user_id.append(row[2])
            raw_intensity.append(row[3])
            steps.append(row[4]) if row[4] > 0 else steps.append(None)
            raw_kind.append(row[5]) 
            heart_rate.append(row[6]) if 250 > row[6] > 10 else heart_rate.append(None)
            unknown_1.append(row[7])
            sleep.append(row[8])
            deep_sleep.append(row[9]) if row[9] != 128 else deep_sleep.append(0)
            rem_sleep.append(row[10]) if row[10] != 128 else rem_sleep.append(0)
            utc_time.append(datetime.datetime.utcfromtimestamp(row[0]).isoformat())
        

    if get_config()["device"] == "Amazfit Band 5":
        for row in rows:
            # append data
            timestamp.append(row[0])
            steps.append(row[4])
            heart_rate.append(row[6])
            raw_kind.append(row[5])

    return timestamp, device_id, user_id, raw_intensity, steps, raw_kind, heart_rate, unknown_1, sleep, deep_sleep, rem_sleep


def csv_write(data, name = "./data/data.csv"):
    time_stamps = data.timestamps
    with open(name, "a", newline='') as f:
        writer = csv.writer(f)
        if f.tell() == 0:  # Check if the file is empty
            writer.writerow(("Time", "Heart", "Steps"))  # Write the header if the file is empty
        for item in time_stamps:
            unix = item
            time = data.get_local_time(item)
            heart = data.get_heartrate(item)
            steps = data.get_steps(item)
            activity_id = data.activity.get_activity_id(item)
            activity_type = data.activity.get_activity_type(item)
            writer.writerow((unix, time, heart, steps, activity_id, activity_type))

def init(location):
    # the function can read from CSV, JSON and SQLITE DB files automatically
    # filetype does not need to be specified, only the location (can be relative)
    location_type = location.split(".")[-1]
    
    # initialise variables
    timestamp = []
    device_id = []
    user_id = []
    raw_intensity = []
    steps = []
    raw_kind = []
    heart_rate = []
    unknown_1 = []
    sleep = []
    deep_sleep = []
    rem_sleep = []

    if location_type == "db":
        global cursor
        conn = sqlite3.connect(location)
        cursor = conn.cursor()
        if get_config()["device"] == "Amazfit Band 5":
            table_name = 'MI_BAND_ACTIVITY_SAMPLE'
        elif get_config()["device"] == "Mi Band 7":
            table_name = 'HUAMI_EXTENDED_ACTIVITY_SAMPLE'
        cursor.execute(f'SELECT * FROM {table_name}')
        timestamp, device_id, user_id, raw_intensity, steps, raw_kind, heart_rate, unknown_1, sleep, deep_sleep, rem_sleep = data_read(cursor)

    elif location_type == "csv":
        with open(location, "r") as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                steps.append(int(row[2])) if row[2] != "" else steps.append(None)
                heart_rate.append(int(row[1])) if row[1] != "" else heart_rate.append(None)
                timestamp.append(int(datetime.datetime.timestamp(datetime.datetime.strptime(row[0],"%Y-%m-%dT%H:%M:%S"))))

    elif location_type == "json":
        with open(location, "r") as f:
            data = json.load(f)
            supported_items = data[str(0)].keys()
            for i in range(len(data)):
                heart_rate.append(data[str(i)].get("heart", None) if "heart" in supported_items else None)
                timestamp.append(data[str(i)].get("unix_time", None) if "unix_time" in supported_items else None)
                steps.append(data[str(i)].get("steps", None) if "steps" in supported_items else None)


    data = Data(timestamps=timestamp, steps_data=steps, heart_data=heart_rate, activity_data=raw_kind, sleep_data=sleep, deep_sleep_data = deep_sleep, rem_sleep_data = rem_sleep)
    return data

def heart_rate_plot(data, offset=10, figsize=(12,6), save=True, dpi=400, zone="22:00:00", show_sleep = False, fancy_ticks = True, show_high_hr = 90, correct_midnights = True):

    plt.figure(figsize=figsize)

    x_points = data.timestamps
    y_points = data.heart
    
    y_points_smooth = correct_nones(y_points)
    y_points_smooth = savgol_filter(y_points_smooth, 21, 2)
    x_points = x_points[0:-1]
    y_points_smooth = y_points_smooth[0:-1]

    midnight_timestamps , _ = data.get_midnight(zone=zone)
    labels = list()

    if fancy_ticks:
        for item in midnight_timestamps: 
            labels.append(data.get_date(item,format="%dth %B"))
    if show_sleep:
        if not data.activity.sleep:
            raise Warning("No sleep data provided but a show_sleep function triggered")
        else:
            for item in data.timestamps:
                if data.activity.sleep[data.timestamps.index(item)]["sleep"] == True:
                    plt.axvspan(item, item+60, facecolor='blue', alpha=0.3)
    if show_high_hr:
        if not data.heart:
            raise Warning("No heartrate data provided but a show_high_hr function triggered")
        for item in data.timestamps:
            hrrate = data.get_heartrate(item)
            if hrrate:
                if hrrate > show_high_hr:
                    plt.axvspan(item, item+60, facecolor='orange', alpha=0.3)
            
    plt.xticks(midnight_timestamps, labels, ha='right')
    plt.ylim(round(min(y_points_smooth)-offset), round(max(y_points_smooth)+offset))
    plt.xlim(x_points[0], x_points[-1])
    plt.plot(x_points, y_points_smooth)
    plt.savefig("./data/figure.png", dpi=dpi) if save else None
    plt.show()

    tm.sleep(20)

# initialisation from config.json file
if get_config()["update_local_db"]:
    data = init(drive.get_folder(get_config()["data_folder_id"], api_key= get_config()["api_key"]))
else:
    data = init("data.db")

if __name__ == "__main__":
    # csv_write(data)

    # as of 2023-07-02 data is no longer global (hence you can get specific ranges using the inbuild data.range())
    heart_rate_plot(data.range(data.get_timestamp("2023-07-10"), data.get_timestamp("2023-07-20")), show_sleep=True)
    # please note that the above method will use UTC time so there will be overflow, if you want to avoid it you can specify the time directly ("2023-06-27T22:00:00")
