.. _clause-config:

Конфигуратор классов
====================

Описание
--------

DefaultConfig - Класс конфигуратор, принимающий при создании три типа классов для инжектирования:
 * repo_cls (наследник AbstractRepository из abstractpipeline.py) - класс бизнес-логики. **Обязательный параметр**.
 * db_cls (наследник AbstractFactory из abstractpipeline.py) - класс работы с базой данных. Если параметр не указан, будет присвоен реализованный класс по умолчанию - :class:`~abstractclient.defaultpipeline.database.DAO` (database.py, см. :ref:`clause-database`).
 * transport_cls (наследник AbstractFactory из abstractpipeline.py) - класс для работы с транспортным протоколом. Если не указан, будет присвоен реализованный класс по умолчанию - :class:`~abstractclient.defaultpipeline.transports.HTTPFactory` (transport.py, см. :ref:`clause-transport`), для работы с протоколом HTTP.

Пример создания конфигуратора, с передачей только обязательного параметра - созданного репозитория ArticleImport,
с единственным методом "Test".

.. code-block:: python
   :emphasize-lines: 8

   class ArticleImport(AbstractRepository):
       @staticmethod
       def test():
           return "OK"

   # Создадим конфигуратор и передадим ему тип класса Репозитория.
   # Остальные классы по умолчанию.
   config_object = DefaultConfig(ArticleImport)


.. _clause-config_file:

Конфигурационные файлы
----------------------
Для запуска фреймворка должны быть заданы несколько переменных окружения:

 * {REPOSITORY_NAME}_ENV=stage | production | development
 * {REPOSITORY_NAME}_MODE=md | mm | mk | и т.п.
 * Опционально: {REPOSITORY_NAME}_CONFIG=/path/to/{repository_name}.production.json

.. important::
   Важно, чтобы переменные окружения были заданы в верхнем регистре. REPOSITORY_NAME - должно полностью совпадать с названием класса репозитория. Так, для вышеприведенного примера, переменная окружения будет выглядеть как **ARTICLEIMPORT_ENV**

После запуска, конфигуратор DefaultConfig осуществляет настройку работы фреймворка по параметрам, которые должны
находится в конфигурационном файле, путь к которму задан в переменной окружения {REPOSITORY_NAME}_CONFIG.
Если данная переменная не задана, то файл конфигурации должен находиться по умолчанию по следующему пути
/etc/{repository_name}/{repository_name}.{repository_name}_env.json.
Пример конфигурационного файла приведен ниже. Он должен содержать три обязательные ветки "main" для общих настроек,
"transport" - для настройки транспорта и "db" - для настройки соединения с базой данных.

.. code-block:: json

   {
     "main": {
       "log_file": "/etc/articleimport/articleimport.logging.json",
       "auto_create_directory": [
          "/var/db/articleimport"
       ]
     },
     "transport": [
       {
         "alias": "headquarter",
         "sessions": [
           {
             "alias": "primary",
             "host": "https://shvili.me",
             "port": 443,
             "username": "user",
             "password": "password",
             "auth_type": "Basic",
             "verify": "/etc/ssl/certs/ca-chain.crt",
             "timeout": 30
           }
         ],
         "default_headers": {
           "X-Service-Version": "1",
           "X-Warehouse-Code": "",
           "X-Message-Id": "",
           "X-Batch-Id": "",
           "X-Batch-Size": "100",
           "X-Entity-Type": "",
           "Content-type": "application/json"
         },
         "scheme": {
           "paths": [
             {
               "alias": "export",
               "url": "whs-gw/export",
               "method": "GET",
               "headers": {
                 "X-Warehouse-Code": "$(whscode)",
                 "X-Batch-Id": "$(batch_id)",
                 "X-Entity-Type": "$(entity_type)",
                 "Content-type": "application/zip"
               }
             },
             {
               "alias": "confirm",
               "url": "whs-gw/confirm",
               "method": "POST",
               "headers": {
                 "X-Warehouse-Code": "$(whscode)",
                 "X-Batch-Id": "$(batch_id)",
                 "X-Entity-Type": "$(entity_type)",
                 "Content-type": "application/json"
               }
             }
           ]
         }
       }
     ],
     "db": [
       {
         "alias": "firebird",
         "connection": {
           "module": "fdb",
           "function": "connect"
         },
         "pool": {
           "pool_size": 50,
           "max_overflow": 20,
           "timeout": 30,
           "use_lifo": true
         },
         "credentials": {
           "user": "admin",
           "password": "pass",
           "charset": "WIN1251"
         }
       }
     ]
   }

Классы модуля
-------------

.. automodule:: abstractclient.defaultpipeline.config

   .. autoclass:: DefaultConfig(params)
      :members:


