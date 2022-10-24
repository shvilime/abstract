.. _clause-repository:

Репозиторий
===========

Описание
--------

Создавая класс с описанием бизнес логики работы приложения, необходимо унаследовать его от AbstractRepository.
Это делает доступным для использования класс database - для работы с базой данных, transport - для работы с
системой пересылки данных по протоколу HTTP, logger - для ведения логов

Классы модуля
-------------

.. automodule:: abstractclient.abstractpipeline

   .. autoclass:: AbstractRepository
      :show-inheritance:
      :members:
