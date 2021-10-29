from pprint import pprint
from builtins import str
import json
from wialon_api import Wialon

from pydantic import BaseModel
from flask import Flask, request
from env import TOKEN


class Address(BaseModel):
    """
    Модель данных адреса
    """
    city: str
    country: str
    formatted_path: str
    house: str
    region: str
    street: str
    x: str
    y: str

class Addresses(BaseModel):
    """
    Модель данных списка адресов
    """
    items: list = []

    def load(self, data: list):
        for address in data:
            self.items.append(Address(**address['items'][0]))

    class Config:
        json_dumps = lambda v, default: json.dumps(v, default=default, ensure_ascii=False)


if __name__ == '__main__':
    if TOKEN == "":
        pprint('Необходимо заполнить токен в файле env.py (переименовать env_example.py в env.py)')
        exit('Не заполнен TOKEN')

    # Инициализация http-сервера
    app = Flask(__name__)

def search_coords_by_phrase(phrase: str) -> Addresses:
    wialon_api = Wialon()
    result_login = wialon_api.token_login(token=TOKEN)
    result = wialon_api.gis_searchintelli(phrase, count=1)
    wialon_api.core_logout()
    addresses = Addresses()
    addresses.load(result)
    return addresses

@app.route('/search', methods=['GET'])
def search_phrase() -> str:
    """
    Функция-событие на GET-запрос. Принимает адрес в произвольной форме
    :return:
    Возвращает JSON-строку со списком найденных адресов в строгой форме с координатами
    """
    phrase = request.args.get('phrase')
    result = search_coords_by_phrase(phrase)
    return result.json()

if __name__ == '__main__':
    # Запуск http-сервера
    app.run(host="0.0.0.0", port=8080)