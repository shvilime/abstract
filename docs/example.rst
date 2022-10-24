.. _clause-example:

Пример использования
====================

Постановка задачи
-----------------
Необходимо реализовать клиент потока данных из ГК в ОО, который получает данные сущности "strange_web_entity" по
протоколу HTTP и записывает ее в Firebird базу данных обособленного отделения, вызывая процедуру "SAVE_STRANGE_ENTITY".

Реализация
----------
Для реализации данной задачи, будут написаны 3 модуля, условные тексты которых приведены ниже.

Поскольку в качестве транспортного протокола используется HTTP, будет использован стандартный транспортный класс -
:class:`~abstractclient.defaultpipeline.transports.HTTPFactory`, поставляемый фреймворком по умолчанию.
Для использования класса HTTPFactory необходимо задать в настроечных файлах модуля (см. :ref:`clause-config_file`)
заголовки посылаемых пакетов данных, а также схему отправки запросов, с указанием url-адресов, по которым
они отправляются.

.. important::
   Обратите внимание на заданные в схеме дополнительные заголовки, которые обязательно нужно будет передать при
   отправке HTTP запроса по данному пути.

Например:

.. code-block:: json

    {
      "alias": "headquarter",
      "sessions": [
        {
          "alias": "primary",
          "host": "https://shvili.me",
          "port": 443,
          "username": "user",
          "password": "assword",
          "auth_type": "Basic",
          "verify": "/etc/ssl/certs/ca-chain.crt",
          "timeout": 30
        }
      ],
      "default_headers": {
        "X-Service-Version": "1",
        "X-Batch-Size": "100",
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

Модуль database.py будет отвечать за сохранение полученных данных в базу Firebird. В нем будет использоваться,
предоставляемый фреймворком класс работы с базой - :class:`~abstractclient.defaultpipeline.database.DAO`.
Наш модуль необходим лишь манипулирования параметрами, при вызове хранимой процедуры базы данных, либо для формирования
сложной логики сохранения даннных из последовательности нескольких запросов и т.д. и т.п. В простых случаях,
реализация данного модуля остается на выбор разработчика и работа с базой может быть реализована прямо в репозитории
с бизнес-логикой, путем вызова методов :meth:`~abstractclient.dba.transaction.execute` или
:meth:`~abstractclient.dba.transaction.callproc`.

.. code-block:: python
   :caption: database.py

   from abstractclient.defaultpipeline.database import DAO

   class DatabaseAPI(DAO):

       def save(self, entity: Dict):
           """
           Сохранить данные
           """
           #  Представим данные сущности в необходимом виде, для передачи параметров в процедуру
           params = [
                 entity.get("name"),
                 entity.get("value")
           ]
           try:
              with self.aquire(True) as tr:
                  tr.callproc("SAVE_STRANGE_ENTITY", params, tr.NOTHING)
              result = 3
           except:
              result = 4

           return result

Модуль repository.py формирует бизнес-логику работы приложения. Последовательность получения данных, их сохранения
в базе данных, формирование подтверждения об обработке, отправку данного подтверждения.

.. _example-repository:

.. code-block:: python
   :caption: repository.py

   from abstractclient.abstractpipeline import AbstractRepository

   class MySuperBusinessLogic(AbstractRepository):

       def run(self) -> bool:
           """
           Запуск обработки сущностей и отправка подтверждений
           """
           result = True
           try:
              # Получим из ГК данные сущности
              batch = uuid.uuid4().hex
              entities: Dict = self.transport["headquarter"].execute(
                    method="export",
                    dynamic_values={"whscode": "332001", "batch_id": batch, "entity_type": "STRANGE_WEB_ENTITY"},
                    extract_strategy=JSONExtractStrategy
              )
              confirms = []
              for entity in entities.items():
                  # Запишем кажду полученную сущность в базу
                  result = self.database["firebird"].save(entity)
                  # Добавим подтверждение об обработке
                  confirms.append({
                          "message_id": entity.get("message_id"),
                          "entity_type": "STRANGE_WEB_ENTITY",
                          "status": result
                  })
              # Отправим подтверждения в ГК
              self.transport.execute(
                  method="confirm",
                  data={"confirms": confirms},
                  dynamic_values={"whscode": "332001", "batch_id": batch, "entity_type": "STRANGE_WEB_ENTITY"}
              )
           except (HTTPError, DatabaseError):
              result = False

           return result

Модуль main.py - основной, вызываемый, модуль приложения. Создает конфигуратор
:class:`~abstractclient.defaultpipeline.config.DefaultConfig` для всех классов, который конфигурирует их,
инжектирует в класс репозитория бизнес-логики. Для удобства работы с репозиторием рекомендую использовать
пакет Click для работы с интерфейсом командной строки. Пример приведен ниже.

.. code-block:: python
   :caption: main.py

   import click
   from abstractclient.defaultpipeline.config import DefaultConfig
   from .database import DatabaseAPI
   from .repository import MySuperBusinessLogic

   @click.group()
   def cli():
       pass

   @cli.command()
   @click.option('--method', type=click.Choice(['imports', 'export']), multiple=True, required=True)
   def run(method):
       for item in method:
           try:
               getattr(repository, item)()
           except Exception as e:
               environment.logger.exception({str(e)})
               continue

   if __name__ == "__main__":
       # Запустим конфигуратор и инжектируем необходимые классы работы с базой и бизнес-логики
       cfg: DefaultConfig = DefaultConfig(repo_cls=MySuperBusinessLogic, db_cls=DatabaseAPI)
       # Получим из конфигуратор экземпляр репозитория для дальнейшей работы
       repository = cfg.repository()
       cli()
