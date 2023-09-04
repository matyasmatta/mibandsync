# uses SQLite database object instead of data class /main/ object as in main.py, migration in 2023-09

# header
import csv
import sqlite3
from sqlite3 import Error
import json
from tqdm import tqdm  # Import tqdm for the progress bar
import datetime
import os
from utils import get_config
from contextlib import contextmanager

# params
CSV_LOCATION = r"D:\Zálohy\Exporty\20230821_6481096885_MiFitness_fr1_data_copy\20230821_6481096885_MiFitness_hlth_center_fitness_data.csv"
DB_LOCATION = r"D:\Dokumenty\Kódování\GitHub-Repozitory\mibandsync\data\main.db"
IGNORE_ERRORS = True
READ_ONLY = False

class Logger:
    def __init__(self, max_file_size_bytes=10 * 1024 * 1024):
        self.filename = "main.log"
        self.max_file_size_bytes = max_file_size_bytes
        self.check_and_create_log_file()

    def check_and_create_log_file(self):
        if not os.path.isfile(self.filename):
            with open(self.filename, "w") as file:
                file.write("")  # Create an empty log file if it doesn't exist

    def get_log_file_size(self):
        return os.path.getsize(self.filename) if os.path.exists(self.filename) else 0

    def write(self, log_type="error", data="", timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.now()

        file_size = self.get_log_file_size()
        if file_size >= self.max_file_size_bytes:
            raise ValueError(f"Log file size exceeds {self.max_file_size_bytes} bytes")

        with open(self.filename, "a") as file:
            log_entry = f"{timestamp} [{log_type.upper()}]: {data}\n"
            file.write(log_entry)

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
            if batch_count % 1000 == 0:
                if get_config()["progress_bars"]: progress_bar.update(1000)

            if activity == "sleep":
                if sleep_start is None:
                    sleep_start = unix_time
            else:
                if sleep_start is not None:
                    # Calculate sleep duration
                    sleep_end = unix_time
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

def data_reader(location=CSV_LOCATION):
    logger = Logger()

    def type_interpret(type):
        if "heart_rate" in type:
            result = "heart_rate"
        elif "heart_rate" in type:
            result = "heart_rate"
        elif "heart_rate" in type:
            result = "heart_rate"
        elif "steps" in type:
            result = "steps"
        elif "calories" in type:
            result = "calories"
        elif "dynamic" in type:
            result = "steps"
        elif "sleep" in type:
            result = "sleep"
        elif "intensity" in type:
            result = "intensity"
        elif "single_spo2" in type:
            result = "spo2"
        elif "stress" in type:
            result = "stress"
        else:
            result = "unknown"  # Handle unknown types
        return result
    
    def data_interpret(data):
        if type == "steps":
            result = data["steps"]
        elif type == "heart_rate":
            result = data["bpm"]
        elif type == "calories":
            result = data["calories"]
        elif type == "sleep":
            if "end_time" in data:
                result = data["end_time"] - data["start_time"]
            elif "bedtime" in data:
                result = data["wake_up_time"] - data["bedtime"]
        elif type == "intensity":
            result = 1
        elif type == "spo2":
            result = data["spo2"]
        elif type == "stress":
            result = data["stress"]
        return result
    
    with open(CSV_LOCATION, "r") as csv_file:
        reader = csv.reader(csv_file)
        data_list = list()
        ERROR_COUNT = int()
        SUCCESSFUL_RUNS = int()
        LENGTH_CSV = sum(1 for row in reader)
        csv_file.seek(0)
        reader = csv.reader(csv_file)
        last_error_print = int()
        if get_config()["progress_bars"]: progress_bar = tqdm(total=LENGTH_CSV, desc="Processing CSV")
        data = None

        for row in reader:
            try:
                source = "mi_fitness_import"
                time = row[3]
                type = type_interpret(row[2])
                data = data_interpret(json.loads(row[4]))
                if type == "sleep":
                    try: 
                        time = (json.loads(row[4]))["bedtime"]
                    except:
                        time = (json.loads(row[4]))["start_time"]
                data_list.append((time, source, type, data))
                SUCCESSFUL_RUNS += 1
            except:
                ERROR_COUNT += 1
                if not IGNORE_ERRORS:
                    if ERROR_COUNT > LENGTH_CSV/10000:
                        raise ImportError("The number of errors in intepretation exceeded 0.1%, this usually means invalid interpretation or wrong data types.") 
                if data: logger.write(log_type="error", data=(row[2], row[4]))
                
            if SUCCESSFUL_RUNS % 1000 == 0:
                if get_config()["progress_bars"]: progress_bar.update(1000)  # Update the progress bar
        if get_config()["progress_bars"]: progress_bar.close()
        print("\n Encountered", ERROR_COUNT, "errors during import.")
        if not READ_ONLY: 
            try:
                db.write_data_bulk(data_list=data_list, command="INSERT INTO DATA_POINTS (UNIX_TIME, SOURCE, TYPE, VALUE) VALUES (?, ?, ?, ?)")
            except sqlite3.Error as e:
                print(e)

if __name__ == "__main__":
    global db
    db = Database(db_file=DB_LOCATION)
    with db.connection() as conn:
        data_reader()
        db.transfer_data()
        Analytics.daily_analysis()

# todo: fix the "dynamic" data type