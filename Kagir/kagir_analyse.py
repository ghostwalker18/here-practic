import requests
import geojson
import re
import pandas as pd
from bs4 import BeautifulSoup

URL = "http://kagir.kz"
MAIN_PAGE = "kg_0501.html"
API_KEY = "RAKy_aPGkcPtrbaAJWcY1bfNX7O5FDVdG_CK5KofTtQ"

def get_data(url=None):
    if url is None:
        return False
    main_page = requests.get(url=URL + "/" + MAIN_PAGE)
    main_page_soup = BeautifulSoup(main_page.text, 'lxml')
    main_page_hrefs = set([])
    for element in main_page_soup.select('a'):
        #Находим по сигнатуре все ссылки на страницы отдельных регионов
        if element['href'].startswith("kg_0501") and len(element['href']) > len("kg_0501.html"):
            main_page_hrefs.add(element['href'])
    #Проходим по всем найденным ссылкам для отдельных регионов и извлекаем ссылки на отдельные заведения
    hotels_hrefs = set([])
    for href in main_page_hrefs:
        region_page = requests.get(url=URL + "/" + href)
        #На сайте сбитая кодировка
        region_page.encoding = 'utf-8'
        region_page_soup = BeautifulSoup(region_page.text, 'lxml')
        for element in region_page_soup.select('a'):
            if element['href'].startswith("kg_0501") and element.string == "Подробнее об отеле":
                hotels_hrefs.add(element['href'])
    info = []
    #Шаблон для удаления звездочек из названия отеля
    rexp1 = re.compile(r'[*][ *]*')
    #На сайте идентификаторы номеров телефонов(Тел.:) записаны в перемешку русскими и латинскими буквами, иногда идентификатор отсутствует
    rexp2 = re.compile(r'[ТтT][еe]л|\+7')
    #Шаблон для очистки вводных данных от остатков разметки html
    rexp3= re.compile(r'\r\n|\n')
    #Шаблон для удаления уточняющих комментариев из адреса
    rexp4 = re.compile(r'\(.+\)')
    #Проходим по ссылкам для отелей и извлекаем адреса, расположенные до номера телефона в строке тега <b>
    for href in hotels_hrefs:
        hotel_page = requests.get(url=URL + "/" + href)
        if hotel_page.status_code != 200:
            continue
        hotel_page.encoding = 'utf-8'
        hotel_page_soup = BeautifulSoup(hotel_page.text, 'lxml')
        name = rexp1.sub("", hotel_page_soup.select("font.t3")[0].text).strip()
        raw_address_info = hotel_page_soup.select("b")[0].text
        raw_address = rexp3.sub(" ", raw_address_info).strip()
        if re.search(pattern=rexp2, string=raw_address) is not None:
            match = re.search(rexp2, raw_address)
            address = raw_address[0:match.start()].strip(' ,')
            clean_address = re.sub(pattern=rexp4, string=address, repl="")
            info.append({'name' : name,'address' : clean_address})

    return pd.DataFrame(info)


def save_data(data=None):
    if data is None:
        return False
    with open('kagir.geojson', 'w', encoding='utf-8') as file:
        geojson.dump(data, file, ensure_ascii=False, indent=4)
        return True


def geocode_line(address, apiKey):
    # Основной домен сервиса геокодирования
    URL = 'https://geocode.search.hereapi.com/v1/geocode'

    # Параметры запроса
    params = {
        'q': address,
        'apiKey': apiKey
    }

    # Парсинг ответа в JSON формате
    response = requests.get(URL, params=params).json()

    result = {
        'address': address,
        'lat': None,
        'lng': None,
    }

    if response is not None:
        if response['items'] is not None and len(response['items']) > 0:
            item = response['items'][0]
            address = item['address']
            position = item['position']
            result = {
                'address': address['label'],
                'lat': position['lat'],
                'lng': position['lng'],
            }
    return result


def geocode_dataframe(data):
    df = pd.DataFrame([geocode_line(address=address, apiKey=API_KEY) for address in data['address']])
    df['name'] = data['name']
    #Выбираем адреса, не прошедшие геокодирование и сохраняем их в отдельный файл
    failed_addresses = df[pd.isnull(df).any(1)]
    failed_addresses = failed_addresses.dropna(axis='columns')
    with open('failed_adresses.csv', 'w', encoding='utf-8') as file:
        failed_addresses.to_csv(file)
    df = df.dropna()
    return df

def to_geojson(data):
    features = []
    for index, row in data.iterrows():
        feature = {
            "type": "Feature",
            "properties": {
                "name": row['name'],
                "address": row['address']
            },
            "geometry": {
                "type": "Point",
                "coordinates": [row['lng'], row['lat']]
            }
        }
        features.append(feature)
    
    featureCollection = {
       "type": "FeatureCollection",
       "features": features
    }

    return featureCollection


def main():
    data = get_data(url=URL)
    if data.empty is False:
        geocoded_data = geocode_dataframe(data)
        if save_data(to_geojson(geocoded_data)):
            print("Successfuly saved")
            procent_of_fail = round((len(geocoded_data.index) / len(data.index)) * 100, 2)
            print("Procent of succesfully geocoded adresses: " + str(procent_of_fail))
        else:
            print("Something went wrong!")


if __name__ == "__main__" :
    main()