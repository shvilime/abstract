.. _clause-database:

Работа с базой
==============

Описание
--------

Класс :class:`~abstractclient.defaultpipeline.database.DAO` реализует многопоточный, транзакционный пул работы с
базой данных. AbstractClient поддерживает одновременную работу с нескольким базами данных. Параметры работы заданы
в виде списка в настроечных файлах модуля (см. :ref:`clause-config_file`) с разными alias,
по которым к ним и происходит обращение к той или иной базе данных (см. пример кода :ref:`example-repository`).

В настройках конфигурационного файла, каждое подключение должно содержать три обязательные ветки:

 - "connection" с обязательным указанием загружаемого "module" - фабрики коннектов к базе,
 - "pool" - настройки пула подключений.
 - "credentials" - параметры подключения, которые переопределят, считываемые по умолчанию настройки local_db.conf (см. :ref:`clause-config_file`)

Классы модуля
-------------

.. automodule:: abstractclient.defaultpipeline.database

   .. autoclass:: DAO
      :show-inheritance:
      :members:
      :inherited-members:
