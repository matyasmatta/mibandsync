import json
import warnings

def init(data, json_out=False):
    result = dict()
    for i in range(len(data.activity.type)):
        result[data.timestamps[i]] = data.activity.type[i]
    if json_out:
        with open("results.json", "w") as f:
            json.dump(result, f, indent=4)
    return result

def get_time_to_asleep(data, json_out=False, debug=False):
    # Debug mode will return whole dictionary even with false data and all variables
    def no_sleep_before(result):
        i = int()
        edges = dict()
        for item in result:
            try:
                if result[item] == "sleeping" and previous_item  != "sleeping":
                    edges[item] = {}
                    edges[item]["time"] = data.get_local_time(item)
                    edges[item]["unix"] = item
                    for i in range(180):
                        i += 1
                        test = result[item-60*i]
                        if test == "sleeping":
                            edges[item]["180min_nosleep"] = False
                            break
                        edges[item]["180min_nosleep"] =  True
                previous_item = result[item]
                i += 1
            except:
                warnings.warn("Minor error: Previous item not defined (due to database starting during sleep). Error handled.", ImportWarning)
        return edges

    def count_activity_before_sleep(edges, result):
        for item in edges:
            i = int()
            moving_count, walking_count = int(), int()
            for i in range(240):
                i += 1
                if result[item-i*60] == "rest_hand_stationary":
                    pass
                if result[item-i*60] == "walking":
                    walking_count += 1
                if result[item-i*60] == "rest_hand_moving":
                    moving_count += 1
                if moving_count > 6 or walking_count > 2 or (moving_count > 4 and walking_count > 1):
                    i = i - moving_count - walking_count
                    break
            edges[item]["time_to_asleep"] = i
        return edges
    
    def get_date_to_sleep(edges):
        # Gets date and sleep type (utc format date and nap/night)
        for item in edges:
            if edges[item]["time_to_asleep"] < 180 and edges[item]["180min_nosleep"] == True:
                # Gets date
                hour = edges[item]["time"][11:13]
                if int(hour) > 12:
                    date = edges[item]["time"][0:10]
                else:
                    date = edges[item]["time"][0:10]
                    day = int(date[8:10])
                    day = day - 1
                    if day < 10:
                        date = edges[item]["time"][0:7] + "-0" + str(day) 
                    else:
                        date = edges[item]["time"][0:7] + "-" + str(day)
                # Gets type
                if 12 < int(hour) < 18:
                    edges[item]["type"] = "nap"
                else:
                    edges[item]["type"] = "night"
                edges[item]["day"] = date
        return edges
    
    def format_edges(edges):
        result = dict()
        for item in edges:
            if edges[item]["time_to_asleep"] < 180 and edges[item]["180min_nosleep"] == True and edges[item]["type"] == "night":
                meta_key = item
                key = edges[meta_key]["day"]
                data = edges[meta_key]["time_to_asleep"]
                result[key] = {}
                result[key]["time_to_asleep"] = data
                result[key]["time_when_went_asleep"] = edges[item]["unix"]
        return result

    formatted_dictionary = init(data, json_out)
    meta_result = no_sleep_before(formatted_dictionary)
    meta_result = count_activity_before_sleep(result=formatted_dictionary, edges=meta_result)
    meta_result = get_date_to_sleep(meta_result)

    if not debug:
        edges = format_edges(meta_result)

    if json_out:
        try:
            with open("edges.json", "w") as f:
                json.dump(edges, f, indent=4)
        except:
            raise ValueError("Fatal error - edges is undefined for: json_out")
    if edges:
        return edges
    else:
        raise  ValueError("Fatal error - edges is undefined for: return")

def get_sleep_length(data, edges={}, json_out=False):
    if edges == {}:
        # Only for emergency-cases
        import main
        edges = get_time_to_asleep(main.init("data.db"))

    # This function requires data from get_time_to_asleep() to know the points when user went asleep
    formatted_dictionary = init(data)
    output = dict()
    for item in edges:
        day = item
        start_time = edges[item]["time_when_went_asleep"]
        i, slept_minutes, current_awake_minutes, awake_minutes = int(), int(), int(), int()
        while True:
            i += 1
            if formatted_dictionary[int(edges[item]["time_when_went_asleep"])+(i*60)] == "sleeping":
                slept_minutes += 1
                current_awake_minutes = 0
            if formatted_dictionary[int(edges[item]["time_when_went_asleep"])+(i*60)] != "sleeping":
                awake_minutes += 1
                current_awake_minutes += 1
            if i > 600:
                if current_awake_minutes > 60:
                    awake_minutes -= current_awake_minutes
                    end_time = int(edges[item]["time_when_went_asleep"])+(i*60) - current_awake_minutes*60
                    break
            else:
                if current_awake_minutes > 120:
                    awake_minutes -= current_awake_minutes
                    end_time = int(edges[item]["time_when_went_asleep"])+(i*60) - current_awake_minutes*60
                    break
            if i == 720:
                warnings.warn("Sleep lenght function couldn't find end of sleep for day:" + str(day) + ", handled accordingly.", FutureWarning)
                end_time = "undefined"
                break
        output[day] = {}
        output[day]["start_time"] = start_time
        output[day]["end_time"] = end_time
        output[day]["slept_minutes"] = slept_minutes
        output[day]["awake_minutes"] = awake_minutes
        
        if json_out:
            with open("sleep.json", "w") as f:
                json.dump(output, f, indent=4)

    return output

if __name__ == "__main__":
    import main
    get_sleep_length(data=main.init("data.db"), json_out=True)
