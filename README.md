# Автобусы на карте Москвы

Веб-приложение показывает передвижение автобусов на карте Москвы.

<img src="screenshots/buses.gif">

## Как запустить

- Скачайте код
- Запустите эмулятор автобусов (ниже инструкция)
- Запустите сервер (ниже инструкция)
- Откройте в браузере файл index.html

### Как запустить эмулятор автобусов

```shell
python fake_bus.py [-h] -server SERVER -rn ROUTES_NUMBER -b BUSES_PER_ROUTE -id EMULATOR_ID [-t REFRESH_TIMEOUT] [-v {0,10,20,30,40,50}]
```

Параметры:

`-h, --help` - помощь

`-server SERVER, --server SERVER` - адрес сервера (вместе с портом)

` -rn ROUTES_NUMBER, --routes_number ROUTES_NUMBER` - количество эмулируемых маршрутов

`-b BUSES_PER_ROUTE, --buses_per_route BUSES_PER_ROUTE` - количество автобусов на маршрут (автоматически будут находиться в разных точках маршрута)

`-id EMULATOR_ID, --emulator_id EMULATOR_ID` - уникальный id эмулятора при запуске нескольких эмуляторов, для понимания инициатора сообщения при логировании

`-t REFRESH_TIMEOUT, --refresh_timeout REFRESH_TIMEOUT` - отправлять новую точку каждые REFRESH_TIMEOUT секунд

`-v {0,10,20,30,40,50}, --verbosity {0,10,20,30,40,50}` - уровень логирования (по умолчанию 0 - без логирования)

### Как запустить сервер

```shell
python server.py [-h] -host HOST -lp BUS_PORT -sp BROWSER_PORT [-v {0,10,20,30,40,50}]
```

Параметры:

`-h, --help` - помощь

`-host HOST, --host HOST` - адрес сервера

`-lp BUS_PORT, --bus_port BUS_PORT` - порт приема сообщений от эмулятора автобусов

`-sp BROWSER_PORT, --browser_port BROWSER_PORT` - порт приему и отправки сообщений браузеру

`-v {0,10,20,30,40,50}, --verbosity {0,10,20,30,40,50}` - уровень логирования (по умолчанию 0 - без логирования)

## Настройки браузера

Внизу справа на странице можно включить отладочный режим логгирования и указать нестандартный адрес веб-сокета.

<img src="screenshots/settings.png">

Настройки сохраняются в Local Storage браузера и не пропадают после обновления страницы. Чтобы сбросить настройки удалите ключи из Local Storage с помощью Chrome Dev Tools —> Вкладка Application —> Local Storage.

Если что-то работает не так, как ожидалось, то начните с включения отладочного режима логгирования.

## Формат данных

Фронтенд ожидает получить от сервера JSON сообщение со списком автобусов:

```js
{
  "msgType": "Buses",
  "buses": [
    {"busId": "c790сс", "lat": 55.7500, "lng": 37.600, "route": "120"},
    {"busId": "a134aa", "lat": 55.7494, "lng": 37.621, "route": "670к"},
  ]
}
```

Те автобусы, что не попали в список `buses` последнего сообщения от сервера будут удалены с карты.

Фронтенд отслеживает перемещение пользователя по карте и отправляет на сервер новые координаты окна:

```js
{
  "msgType": "newBounds",
  "data": {
    "east_lng": 37.65563964843751,
    "north_lat": 55.77367652953477,
    "south_lat": 55.72628839374007,
    "west_lng": 37.54440307617188,
  },
}
```

Сервер ожидает получить от эмулятора JSON сообщение с информацией об автобусе:

```js
{
  "busId": "c790сс",
  "lat": 55.7500,
  "lng": 37.600,
  "route": "120"
}
```

Если сервер получил от браузера или от эмулятора некорректное сообщение, то он отправляет сообщение об ошибке

```js
{
  "msgType": "Errors",
  "errors": [
    {
      "loc": ["data", "east_lng"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Запуск тестов

```pytest tests\```

## Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).
