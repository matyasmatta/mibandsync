# header
import csv
import sqlite3
from sqlite3 import Error
import json
from tqdm import tqdm  # Import tqdm for the progress bar
import datetime
import os
from utils import get_config, correct_nones, Logger
from contextlib import contextmanager
from mi_fitness_convert import data_reader
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
import time
import july

CSV_LOCATION = r"E:\mibandsync_data\20230821_6481096885_MiFitness_hlth_center_fitness_data.csv"
DB_LOCATION = r"E:\mibandsync_data\main.db"
IGNORE_ERRORS = True
READ_ONLY = False

class Data:
    def __init__(self, start_unix, end_unix):
        self.dict = self.fetch_dict(start_unix, end_unix)
        self.heart_rate = self.fetch_list(self.dict, "heart_rate")
        self.steps = self.fetch_list(self.dict, "steps")
        self.sleep = self.fetch_list(self.dict, "sleep")
        self.timestamps = list(self.dict.keys())
    
    def fetch_dict(self, start_unix, end_unix):
        with db.connection() as conn:
            cursor = db.conn.cursor()
            cursor.execute("SELECT UNIX_TIME, STEPS, ACTIVITY, HEART_RATE FROM TIME_POINTS WHERE UNIX_TIME BETWEEN ? AND ?", (start_unix, end_unix))
            rows = cursor.fetchall()
            data_dict = dict()
            for row in rows:
                unix_time, steps, activity, heart_rate = row
                # Assuming unix_time is the date and activity is the sleep value
                # Adjust this based on your table structure
                data_dict[unix_time] = {"sleep": activity, "steps": steps, "heart_rate": heart_rate}
            return data_dict
        
    def fetch_list(self, data_dict=dict, type=type):
        data_list = list()
        for item in data_dict:
            data_list.append(data_dict[item][type])
        return data_list

    def get_midnight(self, zone="22:00:00"): # Set the UTC time which should be marked as midnight (22:00:00 for CEST)
        midnights, days = list(), list()
        for item in self.timestamps:
            current_time = datetime.datetime.utcfromtimestamp(item).isoformat()
            if current_time.endswith(zone):
                midnights.append(item)
                correction_time = 86400 - (int(zone[0:2])*60*60) # There needs to be correction so that it's local time
                days.append(datetime.datetime.utcfromtimestamp(item+correction_time).isoformat()[0:10])
        if midnights == []:
            logger.write(log_type="error", data="When getting midnight data in range Data, none were found, Tools functions might be broken.")
        return midnights, days # Returns the UNIX times for midnights and returns which days those are

class Database:
    @contextmanager
    def connection(self):
        """A context manager for database connections"""
        try:
            if not self.conn:
                self.conn = self.create_connection()
            yield self.conn
        finally:
            if self.conn:
                self.conn.close()

    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = self.create_connection()
        self.create_table()  # Ensure the table exists when an instance is created

    def create_connection(self):
        """ Create a database connection to a SQLite database """
        conn = None
        try:
            # Attempt to connect to the database
            conn = sqlite3.connect(self.db_file)

            # Check if the database is locked by trying to execute a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.close()

            if get_config()["show_sql_version"]:
                print("Connecting to database, current version of SQLite:", sqlite3.version)

            return conn
        except sqlite3.OperationalError as e:
            # Database is locked or some other operational error occurred
            print("SQLite operational error:", e)
            return None


    def create_table(self):
        """ Create the DATA_POINTS table if it doesn't exist """
        if self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS DATA_POINTS (
                        UNIX_TIME INTEGER,
                        SOURCE TEXT,
                        TYPE TEXT,
                        VALUE INTEGER
                    )
                ''')
                self.conn.commit()
            except sqlite3.Error as e:
                print(e)

    def write_data(self, data_list):
        if self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO DATA_POINTS (UNIX_TIME, SOURCE, TYPE, VALUE)
                    VALUES (?, ?, ?, ?)
                ''', data_list)
                self.conn.commit()
            except sqlite3.Error as e:
                print(e)
        
    def write_data_bulk(self, command, data_list):
        if self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.executemany(command, data_list)
                self.conn.commit()
            except sqlite3.Error as e:
                print(e)

    def close_connection(self):
        if self.conn:
            self.conn.close()        

    def transfer_data(self):
        try:
            # Create a cursor for each database connection
            source_cursor = self.conn.cursor()
            destination_cursor = self.conn.cursor()

            # Retrieve data from the source database (adjust the query as needed)
            source_cursor.execute('SELECT UNIX_TIME, SOURCE, TYPE, VALUE FROM DATA_POINTS ORDER BY UNIX_TIME')
            rows = source_cursor.fetchall()

            # Transform and insert data into the destination database
            i = 1
            prev_unix_time = int()
            data_list = list()
            sleep_time = str()
            prev_activity = str()

            if get_config()["progress_bars"]: progress_bar = tqdm(total=len(rows), desc="Sorting and processing SQL")
        
            while i < len(rows):
                try:
                    test = rows[i]
                except:
                    break
                steps, activity, heart_rate, calories = None, None, None, None
                while True:
                    try:
                        test = rows[i]
                    except:
                        break
                    unix_time, source, data_type, value = rows[i]
                    if data_type == "steps":
                        steps = value
                    elif data_type == "sleep":
                        activity = "sleep"
                        prev_activity = "sleep"
                        sleep_time = unix_time
                        sleep_lenght = value
                    elif data_type == "heart_rate":
                        heart_rate = value
                    elif data_type == "calories":
                        calories = value
                    elif data_type == "intensity":
                        activity = "exercise"

                    if prev_activity == "sleep" and unix_time < sleep_time + sleep_lenght:
                        activity = "sleep"
                        prev_activity = "sleep"
                    
                    try:
                        next_unix_time, _, _, _,  = rows[i+1]
                    except:
                        i += 1
                        break
                    i += 1
                    if i % 1000 == 0:
                        if get_config()["progress_bars"]: progress_bar.update(1000)  # Update the progress bar
                    if next_unix_time != unix_time and i > 2:
                        human_time = datetime.datetime.utcfromtimestamp(unix_time).strftime("%Y-%m-%d %H:%M:%S")
                        data_list.append((unix_time, human_time, source, steps, activity, heart_rate, calories))
                        if len(data_list) > 10000:
                            if not READ_ONLY: self.write_data_bulk(data_list=data_list, command='INSERT INTO TIME_POINTS (UNIX_TIME, HUMAN_TIME, SOURCE, STEPS, ACTIVITY, HEART_RATE, CALORIES) VALUES (?, ?, ?, ?, ?, ?, ?)')
                            data_list = list()
                        self.conn.commit()
                        break
            
            if get_config()["progress_bars"]: 
                progress_bar.update(len(rows)-i+100)
                progress_bar.close()
            self.conn.cursor().execute("DELETE FROM TIME_POINTS WHERE UNIX_TIME = 0 OR UNIX_TIME > 2000000000")

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            # Close database connections
            source_cursor.close()
            destination_cursor.close()

class Utils:
    def get_timestamp(time, offset=0): # where time is YYYY-MM-DD(THH:MM:SS)
        # supports either date or time specifically (for ease of use)
        if len(time) == 10:
            time = datetime.datetime.strptime(time, '%Y-%m-%d')
        else:
            time = datetime.datetime.strptime(time, '%Y-%m-%dT%H:%M:%S')
        time_change = datetime.timedelta(hours=offset)
        time = time + time_change
        timestamp = (time - datetime.datetime(1970, 1, 1)).total_seconds()
        return timestamp

    def timedelta_to_human_readable(timedelta_obj):
        seconds = int(timedelta_obj.total_seconds())
        hours, remainder = divmod(seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours}h {minutes}min"

class Analytics:
    def daily_analysis(timezone=0):
        sleep_data = Analytics.get_sleep()
        steps_data = Analytics.get_steps()
        data = Analytics.merge_data(sleep_data, steps_data)
        if get_config()["mi_fitness_json_out"] == True:
            with open("json_out/daily_summary.json", "w") as f: 
                json.dump(data, f, indent=4)
        Analytics.data_to_db(data)
    
    def data_to_db(data):
        if db.conn:
            try:
                human_time, unix_time, steps, sleep = list(), list(), list(), list()
                for key in data.keys():
                    human_time.append(key)
                    unix_time.append(Utils.get_timestamp(key))
                    steps.append(data[key]["steps"])
                    sleep.append(data[key]["sleep"]["seconds"])

                cursor = db.conn.cursor()
                cursor.executemany('''
                    INSERT INTO DAILY_SUMMARY (UNIX_TIME, HUMAN_TIME, STEPS, SLEEP)
                    VALUES (?, ?, ?, ?)
                ''', zip(unix_time, human_time, steps, sleep))
                db.conn.commit()
            except sqlite3.Error as e:
                print(e)

    def merge_data(sleep_data, steps_data):
        merged_data = {}  # Initialize the merged data dictionary
        if get_config()["progress_bars"]: progress_bar = tqdm(total=len(sleep_data.items()), desc="Merging data into a summary")

        # Iterate through the date keys in sleep_data and merge the values
        for date, sleep_seconds in sleep_data.items():
            if date not in merged_data:
                merged_data[date] = {}
            merged_data[date]["sleep"] = {}    
            merged_data[date]["sleep"]["seconds"] = int(sleep_seconds.get("raw", datetime.timedelta()).total_seconds())
            merged_data[date]["sleep"]["hour"] = Utils.timedelta_to_human_readable(sleep_seconds["raw"])
            merged_data[date]["steps"] = steps_data.get(date, 0)
            if get_config()["progress_bars"]: progress_bar.update(1)

        # Iterate through the date keys in steps_data and add any missing dates to merged_data
        for date, steps in steps_data.items():
            if date not in merged_data:
                merged_data[date] = {}
                merged_data[date]["sleep"] = {}
                merged_data[date]["sleep"]["seconds"] = 0
                merged_data[date]["steps"] = steps

        # Sort data by date
        merged_data = dict(sorted(merged_data.items(), key=lambda x: datetime.datetime.strptime(x[0], "%Y-%m-%d")))
        if get_config()["progress_bars"]: progress_bar.close()
        return merged_data

    def get_sleep():
        # Create a connection to the SQLite database
        conn = db.create_connection()
        cursor = conn.cursor()

        # Query the database to retrieve relevant data
        cursor.execute("SELECT UNIX_TIME, ACTIVITY FROM TIME_POINTS")
        rows = cursor.fetchall()

        # Establish a progress bar
        if get_config()["progress_bars"]: progress_bar = tqdm(total=len(rows), desc="Crunching your sleep data")

        # Initialize variables to track sleep duration
        sleep_start = None
        sleep_duration = datetime.timedelta()
        sleep_data = {}  # Dictionary to store sleep durations for each day
        batch_count = 0

        # Iterate through the rows
        for row in rows:
            batch_count += 1
            unix_time, activity = row
            # Initialise var
            if batch_count == 1:
                sleep_end = unix_time
            if batch_count % 1000 == 0:
                if get_config()["progress_bars"]: progress_bar.update(1000)

            if activity == "sleep":
                if sleep_start is None:
                    sleep_start = unix_time
                else:
                    sleep_end = unix_time
            else:
                if sleep_start is not None:
                    try:
                        # Calculate sleep duration
                        try:
                            if unix_time > sleep_end + 120:
                                logger.write(log_type="error", data=("In sleep calculation Mi Band death anomaly detected, handled properly  data invalid, ID:", unix_time, sleep_date))
                            else:
                                sleep_end = unix_time
                        except:
                            logger.write(log_type="error", data=("In sleep calculation sleep_end resulted in NoneType, handled properly data valid, ID:", unix_time, sleep_date))
                        sleep_duration += datetime.timedelta(seconds=(sleep_end - sleep_start))

                        # Determine the date for the sleep data
                        sleep_date = datetime.datetime.utcfromtimestamp(sleep_start).strftime("%Y-%m-%d")

                        # Update the sleep duration for the corresponding date
                        sleep_data[sleep_date] = {}
                        sleep_data[sleep_date]['raw'] = datetime.timedelta()
                        sleep_data[sleep_date]['bedtime'] = {}
                        sleep_data[sleep_date]['waketime'] = {}

                        if sleep_date in sleep_data:
                            sleep_data[sleep_date]['raw'] += sleep_duration
                        else:
                            sleep_data[sleep_date]['raw'] = sleep_duration
                        sleep_data[sleep_date]['bedtime'] = sleep_start
                        sleep_data[sleep_date]['waketime'] = sleep_end
                    except:
                        logger.write(log_type="error", data=("In sleep calculation a general error occured, handled properly data invalid, ID:", unix_time, sleep_date))

                    # Restart vars
                    sleep_start = None
                    sleep_end = None
                    sleep_duration = datetime.timedelta()

        # Ensure the progress bar reaches 100% for any remaining rows
        if get_config()["progress_bars"] and batch_count > 0:
            progress_bar.update(batch_count)
        conn.close()
        if get_config()["progress_bars"]: progress_bar.close()

        return sleep_data

    def get_steps():
        # Create a connection to the SQLite database
        conn = db.create_connection()
        cursor = conn.cursor()

        # Query the database to retrieve relevant data where STEPS > 0
        cursor.execute("SELECT UNIX_TIME, STEPS FROM TIME_POINTS WHERE STEPS > 0")
        rows = cursor.fetchall()

        # Establish a progress bar
        if get_config()["progress_bars"]: progress_bar = tqdm(total=len(rows), desc="Crunching your steps data")

        # Initialize variables to track steps data
        step_data = {}  # Dictionary to store steps data for each day
        batch_count = 0
        # Iterate through the rows
        for row in rows:
            if batch_count % 1000 == 0:
                if get_config()["progress_bars"]:
                    progress_bar.update(1000)
            unix_time, steps = row

            # Determine the date for the steps data
            step_date = datetime.datetime.utcfromtimestamp(unix_time).strftime("%Y-%m-%d")

            # Update the steps data for the corresponding date

            if steps > 200:
                steps = 0

            if step_date in step_data:
                step_data[step_date] += steps
            else:
                step_data[step_date] = steps
            batch_count += 1

        conn.close()
        # Ensure the progress bar reaches 100% for any remaining rows
        if get_config()["progress_bars"]:
            progress_bar.update(1000)
        if get_config()["progress_bars"]: progress_bar.close()
        return step_data

class Tools:
    def heart_rate_plot(start_unix, end_unix, offset=10, figsize=(12,6), save=True, dpi=400, zone="22:00:00", show_sleep = True, fancy_ticks = True, show_high_hr = 90, correct_midnights = True):
        data = Data(start_unix, end_unix)
        plt.figure(figsize=figsize)

        x_points = data.timestamps
        y_points = data.heart_rate
        
        y_points_smooth = correct_nones(y_points)
        y_points_smooth = savgol_filter(y_points_smooth, 300,7) # Default is 27, and 2
        x_points = x_points[0:-1]
        y_points_smooth = y_points_smooth[0:-1]

        midnight_timestamps , _ = data.get_midnight(zone=zone)
        labels = list()

        if fancy_ticks:
            for item in midnight_timestamps: 
                labels.append(datetime.datetime.utcfromtimestamp(item).strftime("%dth %B"))
                
        if show_sleep:
            if not data.sleep:
                raise Warning("No sleep data provided but a show_sleep function triggered")
            else:
                if get_config()["progress_bars"]: progress_bar = tqdm(total=len(data.timestamps), desc="Filling in sleep segments:")
                for item in data.timestamps:
                    if data.dict[item]["sleep"] == "sleep":
                        plt.axvspan(item, item+60, facecolor='blue', alpha=0.3)
                    if get_config()["progress_bars"]: progress_bar.update(1)
                progress_bar.close()
        if show_high_hr:
            if not data.heart_rate:
                raise Warning("No heartrate data provided but a show_high_hr function triggered")
            if get_config()["progress_bars"]: progress_bar = tqdm(total=len(data.timestamps), desc="Filling in high-HR segments:")
            for item in data.timestamps:
                hrrate = data.dict[item]["heart_rate"]
                if hrrate:
                    if hrrate > show_high_hr:
                        plt.axvspan(item, item+60, facecolor='orange', alpha=0.3)
                if get_config()["progress_bars"]: progress_bar.update(1)
            if get_config()["progress_bars"]:progress_bar.close()

        plt.xticks(midnight_timestamps, labels, ha='right')
        plt.ylim(round(min(y_points_smooth)-offset), round(max(y_points_smooth)+offset))
        plt.xlim(x_points[0], x_points[-1])
        plt.plot(x_points, y_points_smooth)
        plt.savefig("./data/figure.png", dpi=dpi) if save else None
        plt.show()

        time.sleep(20)

    def heat_map(start_unix, end_unix, datatype, smooth_data=True):
        def get_time(data):
            return list(data.keys())
        def get_val(data, datatype="steps"):
            result = list()
            for item in data:
                result.append(data[item][datatype])
            return result

        data = Tools.daily_summary(start_unix, end_unix)
        dates = get_time(data)
        values = get_val(data, datatype)
        if smooth_data:
            values = correct_nones(values)
        print(values)
        heatmap = july.heatmap(dates, values, title="Daily summary of " + datatype, cmap="github", month_grid=True)
        plt.show()
        time.sleep(20)
        
    def daily_summary(start_unix, end_unix):
        with db.connection() as conn:
            cursor = db.conn.cursor()
            cursor.execute("SELECT UNIX_TIME, HUMAN_TIME, STEPS, AVERAGE_HR, SLEEP FROM DAILY_SUMMARY WHERE UNIX_TIME BETWEEN ? AND ?", (start_unix, end_unix))
            rows = cursor.fetchall()
            data_dict = dict()
            for row in rows:
                unix_time, human_time, steps, heart_rate, sleep = row
                # Assuming unix_time is the date and activity is the sleep value
                # Adjust this based on your table structure
                data_dict[human_time] = {"sleep": sleep, "steps": steps, "heart_rate": heart_rate}
            return data_dict

if __name__ == "__main__":
    global db, logger, data
    logger = Logger()
    db = Database(DB_LOCATION)
    Tools.heart_rate_plot(start_unix=1684823820, end_unix=1685379900)
    # Tools.heat_map(start_unix=1656700800, end_unix=1686700800, datatype="sleep", smooth_data=True)