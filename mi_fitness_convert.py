# uses SQLite database object instead of data class /main/ object as in main.py, migration in 2023-09

# header
import csv
import sqlite3
from sqlite3 import Error
import json
from tqdm import tqdm  # Import tqdm for the progress bar
import datetime
import os
from utils import get_config, correct_nones
from contextlib import contextmanager

# params
CSV_LOCATION = r"D:\Zálohy\Exporty\20230821_6481096885_MiFitness_fr1_data_copy\20230821_6481096885_MiFitness_hlth_center_fitness_data.csv"
DB_LOCATION = r"D:\Dokumenty\Kódování\GitHub-Repozitory\mibandsync\data\main.db"
IGNORE_ERRORS = True
READ_ONLY = False

def data_reader(location=CSV_LOCATION):
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
    data_reader()

# todo: fix the "dynamic" data type