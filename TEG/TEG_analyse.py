import requests
import geojson
import pandas as pd
import re
from bs4 import BeautifulSoup

URL = "https://teg.al/planimetry/stores-en.html#cod-abp-"
ADDRESS_URL = "https://teg.al/en/contact-us"
API_KEY = "RAKy_aPGkcPtrbaAJWcY1bfNX7O5FDVdG_CK5KofTtQ"

def get_data(url=None):
    if url is None:
        return False
    #Получаем адрес торгового центра
    contact_us_page = requests.get(url=ADDRESS_URL)
    contact_us_page_soup = BeautifulSoup(contact_us_page.text, 'lxml')
    address = contact_us_page_soup.find(name='h3', text='Address:').parent.text.split('\n')[0]
    clean_address = address.replace("Address: ", "")
    stores_hrefs = set()
    #Обманываем JS сайта для получения cсылок на магазины 
    for i in range(1,11):
        url = URL + str(i)
        stores_menu_page = requests.get(url=url)
        stores_menu_page_soup = BeautifulSoup(stores_menu_page.text, 'lxml')
        for element in stores_menu_page_soup.select('a'):
            if element['href'].find("https://teg.al/en/stores-total/") == 0:
                stores_hrefs.add((element['href'], element.text.strip()))
    info = []
    for href, name in stores_hrefs:
        store_page = requests.get(url=href)
        #Далеко не все найденные ссылки действительны
        if store_page.status_code != 200:
            continue
        store_page.encoding = 'utf-8'
        store_page_soup = BeautifulSoup(store_page.text, 'lxml')
        working_hours = store_page_soup.find(name='h1', text='Opening hours').parent.text.strip().split('\r\n')[1]
        #Приводим строку с рабочими часами к более приятному виду
        working_hours = working_hours.replace("   ", "\n")
        info.append({'name': name, 'address': clean_address, 'working_hours':  working_hours})
        df = pd.DataFrame(info)

    return df


def save_data(data=None):
    if data is None:
        return False
    with open('TEG.geojson', 'w', encoding='utf-8') as file:
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
    df['working_hours'] = data['working_hours']
    df = df.dropna()
    return df


def to_geojson(data):
    features = []
    df = geocode_dataframe(data)
    for index, row in df.iterrows():
        feature = {
            "type": "Feature",
            "properties": {
                "name": row['name'],
                "address": row['address'],
                "working_hours": row['working_hours']
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
        if save_data(to_geojson(data)):
            print("Successfuly saved")
        else:
            print("Something went wrong!")
    

if __name__ == "__main__" :
    main()