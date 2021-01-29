import requests
import geojson
import pandas as pd
from bs4 import BeautifulSoup

URL = "https://restexpert.ru/catalog/search"
API_KEY = "RAKy_aPGkcPtrbaAJWcY1bfNX7O5FDVdG_CK5KofTtQ"

def get_data(url=None):
    if URL is None:
        return False
    locations_list = []
    #При попытке обратиться к 43 и выше странице выдачи поиска сервер выдает ошибку
    for i in range(1,3):
        params = {
        'placeType': 'geo',
        'placeUri': 'russia',
        'typeFilter': '1',
        'search': '',
        'page': str(i)
        }
        response = requests.get(url=URL, params=params)
        soap = BeautifulSoup(response.text, 'lxml')
        for element in soap.select('.location > .bs-tooltip'):
            locations_list.append(element.string)
    return locations_list


def save_data(data=None):
    if data is None:
        return False
    with open('restexpert.geojson', 'w', encoding='utf-8') as file:
        geojson.dump(data, file, ensure_ascii=False, indent=4)
        return True


def geocode(address, apiKey):
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


def to_geojson(data):
    features = []
    df = pd.DataFrame([geocode(address=adress, apiKey=API_KEY) for adress in data])
    for index, row in df.iterrows():
        feature = {
           "type": "Feature",
           "properties": {
                "address": row['address'],
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
    if data:
        if save_data(to_geojson(data)):
            print("Successfully saved")
        else:
            print("Something went wrong!")


if __name__ == "__main__" :
    main()