# wialon_api
Скрипт поднимает http-сервер на порту 8080 и принимает GET-запрос c произвольным адресом и возвращает список адресов в строгом формате с координатами.
Скрипт сделан на основе https://github.com/wialon/python-wialon.

## Настройка
- Скопировать env_example.py в env.py
- Заполнить TOKEN

## Запрос
```html
http://<host>:8080/search?phrase="Краснодар, Автомобильная 10"
```
## Ответ
  ```json
  {
    "items":
    [
      {
        "city": "Краснодар",
        "country": "Россия",
        "formatted_path": "Автомобильная ул., Краснодар, Краснодарский край, Россия",
        "house": "",
        "region": "Краснодарский край",
        "street": "Автомобильная ул.",
        "x": "38.9971199036",
        "y": "45.0917396545"
      }
    ]
  }
  ```
