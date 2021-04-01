import time
import requests
import csv
import bs4
import googlemaps

# задаем значения для скраппинга
offer_quantity = 181
pages_quantity = 7

with open("api_key.txt", "r") as file:
    api_key = file.readline()
gmaps = googlemaps.Client(key=api_key)

# скачиваем html документы
def requests_site(N):
    headers = ({'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Safari/605.1.15'})
    for i in range(1,N+1,1):
        url = "https://www.cian.ru/cat.php?deal_type=rent&district%5B0%5D=21&engine_version=2&offer_type=offices&office_type%5B0%5D=2&p=" + str(i)
        response = requests.get(url, headers = headers)

        if response.status_code == 200:
            name = f'sheets/sheet_{i}.txt'
            with open(name, 'w') as f:
                f.write(response.text)
        else:
            print(f"От страницы {i} пришел ответ response.status_code = {response.status_code}")
        time.sleep(6)

# парсим html страницы, и записываем данные в 'cian/data.csv'

def parse_data(N):
    name = 'cian/data.csv'
    data_file = open(name, 'w', encoding='UTF-8')
    writer = csv.writer(data_file, delimiter='\t')
    writer.writerow(['Адрес', 'Цена кв.метра в год, руб.', "Координаты", "Стоимость аренды 100кв.метров в месяц", 'lat', 'lng'])
    count = 0
    for i in range(1,N+1,1):
        html_file_name = f'sheets/sheet_{i}.txt'
        with open(html_file_name, 'rb') as html:
            soup_obj = bs4.BeautifulSoup(html, 'html.parser')
        offers = soup_obj.find_all('div', class_='_93444fe79c--commercialWrapper--fYaWL')
        for offer in offers:
            count += 1
            if count == offer_quantity+1:
                break
            if i == 1:
                offer_addr = offer.find_all('span')[2].get('content')
                if offer_addr == None:
                    offer_addr = offer.find_all('span')[1].get('content')
            else:
                offer_addr = offer.find_all('span')[1].get('content')
                if offer_addr == None:
                    offer_addr  = offer.find_all('span')[2].get('content')

            offer_price = offer.find_all('li', class_ = "c6e8ba5398--header-subTerm-item--1pUL4")
            if offer_addr == None:
                continue
            else:
                offer_coordinates = gmaps.geocode(offer_addr)
                writer.writerow([offer_addr,
                                 offer_price[1].text,
                                 offer_coordinates[0]['geometry']['location'],
                                 calculate_month_rent_cost(offer_price[1].text),
                                 offer_coordinates[0]['geometry']['location']['lat'],
                                 offer_coordinates[0]['geometry']['location']['lng']])
    data_file.close()



# функция обрабатывает строку с ценой из html документов, и возвращает цену объекта в 100м

def calculate_month_rent_cost(year_cost_per_metr):
    if year_cost_per_metr[0] == 'о':
        for_converse = year_cost_per_metr[3:-14].replace(' ', '')
    else:
        for_converse = year_cost_per_metr[:-17].replace(' ', '')
    return int(for_converse) * 100 / 12

# requests_site(pages_quantity)
# parse_data(pages_quantity)