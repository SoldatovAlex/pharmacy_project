import googlemaps
import time
import pandas as pd
import csv
from geopy.distance import geodesic
import gmaps



with open("api_key.txt", "r") as file:
    api_key = file.readline()
gmaps = googlemaps.Client(key=api_key)


hamovniki_coordinates = gmaps.geocode("Хамовники, Москва")

# функция делает запрос к api gmaps и создает 'pharmacy/data.csv' с данными по аптекам

def create_pharmacy_base():
    name = 'pharmacy/data.csv'
    data_file = open(name, 'w', encoding='UTF-8')
    writer = csv.writer(data_file, delimiter='\t')
    writer.writerow(['Координаты', 'Название аптеки', "lat", "lng"])

    hamovniki_coordinates = gmaps.geocode("Хамовники, Москва")
    next_page_token = "first page"
    count = 0
    while(next_page_token != None) and count != 3 :
        if count != 0:
            try:
                next_page_token = query_result["next_page_token"]
            except:
                break
        if count == 0:
            query_result = gmaps.places(query='Pharmacy', location = hamovniki_coordinates[0]['geometry']['location'])
        else:
            query_result = gmaps.places(query='Pharmacy', page_token = next_page_token)
        for pharmacy in query_result["results"]:
            writer.writerow([pharmacy["geometry"]["location"],
                             pharmacy["name"],
                             pharmacy["geometry"]["location"]["lat"],
                             pharmacy["geometry"]["location"]["lng"]])
        count += 1
        time.sleep(3)

    data_file.close()


# функция принимает строку и возвращает кортеж float. Необходимо для дальнейшей работы с координатами
def reverse_str(bad_str):
    ind_comma = bad_str.index(")")
    new_str = bad_str[7:ind_comma]
    space_ind = new_str.index(" ")
    lat = new_str[space_ind+1:]
    lng = new_str[:space_ind]
    return (float(lat), float(lng))

# функция для рассчета P. Принимает расстояние, в зависимости от него считает вероятность
def calculate_P(value):
    if value > 1:
        return 0
    elif value < 0.1:
        return 0.95
    elif value < 0.13:
        return 0.89
    elif value > 0.9:
        return 0.05
    elif value > 0.95:
        return 0.02
    else:
        coef = 1/(value*10)
        return coef

# функция для приведения к диапазону 0-1.
def convert_norm_form(value, from1, from2):
    return (value - from1) / (from2 - from1) * (1 - 0) + 0;

# создаем csv с результатами вычислений новых значений.
def create_result_csv():

    ph_data_path = "pharmacy/data.csv"
    try:
        pharmacy_base = pd.read_csv(ph_data_path, sep='\t')
    except FileNotFoundError:
        print("К сожалению, файл  отсутствует в директории")

    cian_data_path = "cian/data.csv"
    try:
        cian_base = pd.read_csv(cian_data_path, sep='\t')
    except FileNotFoundError:
        print("К сожалению, файл  отсутствует в директории")

    input_data_path = "hamovniki.csv"
    try:
        input_data = pd.read_csv(input_data_path, sep=';')
    except FileNotFoundError:
        print("К сожалению, файл  отсутствует в директории")

    # считываем значения в списки. Что лежит в списках можно понять по названиям
    cian_lat = cian_base['lat'].to_list()
    cian_lng = cian_base['lng'].to_list()
    cian_price = cian_base['Стоимость аренды 100кв.метров в месяц'].to_list()

    ph_lat = pharmacy_base['lat'].to_list()
    ph_lng = pharmacy_base['lng'].to_list()

    traffic_list = input_data["MonthlyPeoples"].to_list() #

    heatmap_point_arr = input_data['HeatmapPoint'].to_list() #

    # создаем списки, которые понадобятся для вычислений и хранения новых значений
    coordinate_arr = []
    minimal_distance_to_ph_list = []
    coefficient_P = []
    coordinate_rent_cost = []
    normalize_price_arr = []
    normalize_traffic_arr = []
    relative_value_heatmap = []
    lan_list = []
    lng_list = []

    # для ema делим расстояние в километр на диапазоны по 50 метров и считаем коэфф для каждого диапазона
    diap_list = []
    for i in range(21):
        i *= 0.05
        diap_list.append(i)

    coeff_for_calc_cost = []

    for diap in diap_list:
        if diap == 0.0:
            coeff_for_calc_cost.append(1)
        elif diap == 0.05:
            coeff_for_calc_cost.append(0.95)
        elif diap == 0.1:
            coeff_for_calc_cost.append(0.9)
        else:
            coeff_for_calc_cost.append(1 / (diap * 10))

    # из hamovniki.csv берем координаты точек и преобразуем к значениям пригодным для вычислений. Осуществляем приведение типов
    for point in heatmap_point_arr:
        tuple_result = reverse_str(point)
        lan_list.append(tuple_result[0])
        lng_list.append(tuple_result[1])
        coordinate_arr.append(tuple_result)
    # запускаем цикл в котором для каждой кооординаты будем считать новые значения
    for coordinate in coordinate_arr:
        distance_to_all_pharmacy = []
        distance_to_all_rent = []
        indexes_price = []
        # считаем P, добавляем значение
        for index in range(len(ph_lat)):
            dist = geodesic(coordinate, (ph_lat[index], ph_lng[index])).km
            distance_to_all_pharmacy.append(dist)
        min_value = min(distance_to_all_pharmacy)
        minimal_distance_to_ph_list.append(min_value)
        coefficient_P.append(calculate_P(min_value))

        # считаем все предложения об аренде что попали от точки в радиус 1км. в indexes_price лежат цены этих
        for index in range(len(cian_lat)):
            distance = geodesic(coordinate, (cian_lat[index], cian_lng[index])).km
            if distance < 1:
                distance_to_all_rent.append(distance)
                indexes_price.append(index)
            else:
                continue

        # если в радиусе км нет предложений об аренде в цену для координаты записываем -1.
        if len(distance_to_all_rent) == 0:
            coordinate_rent_cost.append(-1)
        # считаем по ema цену аренды для координаты
        else:
            chisl = 0
            znam = 0
            for index, dist in enumerate(distance_to_all_rent):
                for ind, diap in enumerate(diap_list):
                    last_ind = (len(diap_list)-1) - ind
                    if last_ind == 0:
                        break
                    elif dist < diap_list[last_ind] and dist > diap_list[last_ind-1]:
                        chisl += coeff_for_calc_cost[ind] * cian_price[indexes_price[index]]
                        znam += coeff_for_calc_cost[ind]
                        break
                    else:
                        continue
            coordinate_rent_cost.append(chisl/znam)

    # для нормализации высчитываем нижнюю и верхнюю границы диапазона coordinate_rent_cost
    min_rent_cost = min(coordinate_rent_cost)
    max_rent_cost = max(coordinate_rent_cost)
    # для нормализации высчитываем нижнюю и верхнюю границы диапазона traffic_list
    max_traffic =  max(traffic_list)
    min_traffic = min(traffic_list)
    #  нормализуем траффик, цену и заполняем список relative_value_heatmap.
    for index, cost in enumerate(coordinate_rent_cost):
        if cost == -1:
            norm_price_for_cost = 1
        else:
            norm_price_for_cost = convert_norm_form(cost, min_rent_cost, max_rent_cost)

        norm_traffic = convert_norm_form(traffic_list[index], min_traffic, max_traffic)

        normalize_traffic_arr.append(norm_traffic)
        normalize_price_arr.append(norm_price_for_cost)
        relative_value = norm_traffic * (1-coefficient_P[index]) * abs(norm_price_for_cost - 1)
        relative_value_heatmap.append(relative_value)

    #  нормализуем relative_value_heatmap
    min_relative_value = min(relative_value_heatmap)
    max_relative_value = max(relative_value_heatmap)
    normalize_relative_value = []
    for value in relative_value_heatmap:
        norm_value = convert_norm_form(value, min_relative_value, max_relative_value)
        normalize_relative_value.append(norm_value)

    # создаем result.csv, с новыми значениями
    result_df = input_data.copy()
    result_df["CoordinateLan"] = lan_list
    result_df['CoordinateLng'] = lng_list
    result_df["P"] = coefficient_P
    result_df["RentCost"] = coordinate_rent_cost
    result_df["NormalizeRentCost"] = normalize_price_arr
    result_df["NormalizeTraffic"] = normalize_traffic_arr
    result_df["RelativeValue"] = normalize_relative_value
    result_df.to_csv('result.csv', index=False)


# create_pharmacy_base()
# create_result_csv()

# Для редактирования:
# 1. relative_value 205 строка. По этому значению будем строить heatmap
# 2. вероятность считаем в цикле на строке 152, там вызывается функция рассчета P, которая объявлена на строке 58
# 3. вычисление цены для координаты описаны со строки 159 по 186