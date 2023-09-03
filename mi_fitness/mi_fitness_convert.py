# uses SQLite database object instead of data class /main/ object as in main.py, migration in 2023-09

# header
import csv
import sqlite3
from sqlite3 import Error
import json
from tqdm import tqdm  # Import tqdm for the progress bar
import datetime
import os

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
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = self.create_connection()
        self.create_table()  # Ensure the table exists when an instance is created

    def create_connection(self):
        """ Create a database connection to a SQLite database """
        conn = None
        try:
            conn = sqlite3.connect(self.db_file)
            print(sqlite3.version)
            return conn
        except sqlite3.Error as e:
            print(e)
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

            progress_bar = tqdm(total=len(rows), desc="Sorting and processing SQL")
        
            while True:
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
                        activity = "workout"

                    if prev_activity == "sleep" and unix_time < sleep_time + sleep_lenght:
                        activity = "sleep"
                        prev_activity = "sleep"
                    
                    try:
                        next_unix_time, _, _, _,  = rows[i+1]
                    except:
                        break
                    i += 1
                    if i % 1000 == 0:
                        progress_bar.update(1000)  # Update the progress bar
                    if next_unix_time != unix_time and i > 2:
                        human_time = datetime.datetime.utcfromtimestamp(unix_time).strftime("%Y-%m-%d %H:%M:%S")
                        data_list.append((unix_time, human_time, source, steps, activity, heart_rate, calories))
                        if len(data_list) > 10000:
                            if not READ_ONLY: self.write_data_bulk(data_list=data_list, command='INSERT INTO TIME_POINTS (UNIX_TIME, HUMAN_TIME, SOURCE, STEPS, ACTIVITY, HEART_RATE, CALORIES) VALUES (?, ?, ?, ?, ?, ?, ?)')
                            data_list = list()
                        self.conn.commit()
                        break

            progress_bar.close()
            print("Data transfer completed successfully.")

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            # Close database connections
            source_cursor.close()
            destination_cursor.close()


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
        db = Database(DB_LOCATION)
        data_list = list()
        ERROR_COUNT = int()
        SUCCESSFUL_RUNS = int()
        LENGTH_CSV = sum(1 for row in reader)
        csv_file.seek(0)
        reader = csv.reader(csv_file)
        last_error_print = int()
        progress_bar = tqdm(total=LENGTH_CSV, desc="Processing CSV")
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
                progress_bar.update(1000)  # Update the progress bar
        progress_bar.close()
        print("\n Encountered", ERROR_COUNT, "errors during import.")
        if not READ_ONLY: db.write_data_bulk(data_list=data_list, command="INSERT INTO DATA_POINTS (UNIX_TIME, SOURCE, TYPE, VALUE) VALUES (?, ?, ?, ?)")

if __name__ == "__main__":
    db = Database(db_file=DB_LOCATION)
    db.transfer_data()

# todo: fix the "dynamic" data type