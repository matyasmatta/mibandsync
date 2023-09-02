# uses SQLite database object instead of data class /main/ object as in main.py, migration in 2023-09

# header
import csv
import sqlite3
from sqlite3 import Error
import json

# params
CSV_LOCATION = r"D:\Zálohy\Exporty\20230821_6481096885_MiFitness_fr1_data_copy\20230821_6481096885_MiFitness_hlth_center_fitness_data.csv"
DB_LOCATION = r"D:\Dokumenty\Kódování\GitHub-Repozitory\mibandsync\data\main.db"

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
        
    def write_data_bulk(self, data_list):
        if self.conn:
            try:
                cursor = self.conn.cursor()
                cursor.executemany('''
                    INSERT INTO DATA_POINTS (UNIX_TIME, SOURCE, TYPE, VALUE)
                    VALUES (?, ?, ?, ?)
                ''', data_list)
                self.conn.commit()
            except sqlite3.Error as e:
                print(e)

    def close_connection(self):
        if self.conn:
            self.conn.close()


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
        return result
            
    with open(CSV_LOCATION, "r") as csv_file:
        reader = csv.reader(csv_file)
        db = Database(DB_LOCATION)
        data_list = list()
        ERROR_COUNT = int()
        SUCCESSFUL_RUNS = int()
        LENGHT_CSV = sum(1 for row in csv_file)

        for row in reader:
            try:
                source = "mi_fitness_import"
                time = row[3]
                type = type_interpret(row[2])
                data = data_interpret(json.loads(row[4]))
                data_list.append((time, source, type, data))
                SUCCESSFUL_RUNS += 1
            except:
                ERROR_COUNT += 1
                if ERROR_COUNT > 100000:
                    raise ImportError("The number of errors in intepretation exceeded regular, this usually means invalid interpretation or wrong data types.")   
            if SUCCESSFUL_RUNS % 1000:
                print("Parsed", SUCCESSFUL_RUNS, "out of", LENGHT_CSV)
        db.write_data_bulk(data_list)
data_reader()