import analysis
import main
import numpy as np
from datetime import datetime, timedelta
from utils import get_config
import json

def calculate_mhi(start_date, end_date):
    def get_range(start_date=start_date, end_date=end_date):
        start_date_str = start_date
        end_date_str = end_date

        # Convert date strings to datetime objects
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        # Create an empty list to store the dates
        date_list = []

        # Loop through the dates from start to end and add them to the list
        current_date = start_date
        while current_date <= end_date:
            date_list.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        return date_list
    
    date_list = get_range()
    data = main.init()
    daily_summary = main.daily_summary(data)
    sl_to_sleep = analysis.get_time_to_asleep(data)
    sl_length = analysis.get_sleep_length(data, sl_to_sleep)
    result_index = float()

    if get_config()["mhi_json_out"]:
        global export_dict
        export_dict = dict()

    for day in date_list:
        if get_config()["mhi_json_out"]: export_dict[day] = {}
        steps_index = 0.4*calculate_steps_index(day, daily_summary)
        sleep_index = 0.3*calculate_sleep_index(day, sl_to_sleep, sl_length)
        activity_index = 0.3*calculate_activity_index(day)

        result_index += (steps_index + sleep_index + activity_index)
    
    if get_config()["mhi_json_out"]:
        with open("json_out/mhi.json", "w") as f:
            json.dump(export_dict, f, indent=4)

    return result_index*100


def calculate_sleep_index(day, sl_to_sleep, sl_length):

    def calculate_lenght_index(day = day, length = sl_length):
        sleep_time = length[day]["slept_minutes"]
        sleep_time /= 60
        index = 1/(1+np.exp(-(sleep_time-8.2)/(2)))
        index /= 7
        if get_config()["mhi_json_out"]: 
            export_dict[day]["sleep"]["lenght"] = {}
            export_dict[day]["sleep"]["lenght"]["raw"] = sleep_time
            export_dict[day]["sleep"]["lenght"]["score"] = index*7
        return index

    def calculate_awake_index(day = day, length = sl_length):
        awake_minutes = length[day]["awake_minutes"]
        index = 1.12-(1/(1+np.exp(-(awake_minutes-20)/(10))))
        index /= 7
        if get_config()["mhi_json_out"]: 
            export_dict[day]["sleep"]["awake"] = {}
            export_dict[day]["sleep"]["awake"]["raw"] = awake_minutes
            export_dict[day]["sleep"]["awake"]["score"] = index*7
        return index
    
    def calculate_to_asleep_index(day = day, to_sleep = sl_to_sleep):
        time_till_asleep = to_sleep[day]["time_to_asleep"]
        index = 1-(1/(1+np.exp(-(time_till_asleep-50)/(10))))
        index /= 7
        if get_config()["mhi_json_out"]: 
            export_dict[day]["sleep"]["till_asleep"] = {}
            export_dict[day]["sleep"]["till_asleep"]["raw"] = time_till_asleep
            export_dict[day]["sleep"]["till_asleep"]["score"] = index*7
        return index

    if get_config()["mhi_json_out"]: export_dict[day]["sleep"] = {}
    index = (0.5*calculate_lenght_index()) + (0.25*calculate_awake_index()) + (0.25*calculate_to_asleep_index())
    return index

def calculate_steps_index(day, daily_summary):
    steps = daily_summary[day]["steps"]
    index = 1/(1+np.exp(-(steps-10000)/(4790)))
    index /= 7
    if get_config()["mhi_json_out"]: 
        export_dict[day]["steps"] = {}
        export_dict[day]["steps"]["raw"] = steps
        export_dict[day]["steps"]["score"] = index*7
    return index

def calculate_activity_index(day):
    index = 0.5/7
    if get_config()["mhi_json_out"]: 
        export_dict[day]["activity"] = {}
        export_dict[day]["activity"]["score"] = index*7
    return index

print(calculate_mhi("2023-07-10", "2023-07-16"))
