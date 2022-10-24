.. _clause-transport:

Работа с HTTP
=============

Описание
--------

Транспортный класс HTTPFactory поддерживает одновременную работу с несколькими источниками данных,
которые заданы в виде списка в настроечных файлах модуля (см. :ref:`clause-config_file`) с разными alias,
по которым к ним и происходит обращение (см. пример кода :ref:`example-repository`).

Кроме того, в рамках источника данных, можно задавать настройки основного и дополнительного адресов подключения
(так называемых, sessions), которые последовательно вызываются в цикле, до получения "рабочего" ответа от источника.
Если только ни один из адресов не вернул приемлимый ответ, то будет сгенерирована ошибка подключения.

Для извлечения данных из ответа, класс HTTPFactory использует extract стратегии. Стратегия извлечения зависит от
заголовков ответа HTTP сервера.

.. table:: Стратегии по умолчанию

    +--------------------------+------------------------+
    | Тип заголовка            | Стратегия              |
    +==========================+========================+
    | application/json         | JSONExtractStrategy    |
    +--------------------------+------------------------+
    | application/xml          | XMLExtractStrategy     |
    +--------------------------+------------------------+
    | application/zip          | ZIPJSONExtractStrategy |
    +--------------------------+------------------------+
    | application/octet-stream | NullExtractStrategy    |
    +--------------------------+------------------------+
    | text/html                | NullExtractStrategy    |
    +--------------------------+------------------------+
    | text/plain               | NullExtractStrategy    |
    +--------------------------+------------------------+

Можно переопределить стратегию или реализовать специализированную стратегию извлечения данных, передавая ее в качестве
параметра методу :meth:`~abstractclient.defaultpipeline.transports.execute`. Кастомная стратегия должна наследоваться
от класса :class:`~abstractclient.abstractpipeline.AbstractStrategy` и должна реализовывать единственный метод
:meth:`~abstractclient.abstractpipeline.AbstractStrategy.extract`
(см. например, :class:`~abstractclient.http.strategies.JSONExtractStrategy`)


Классы модуля
-------------

.. automodule:: abstractclient.defaultpipeline.transports
   :show-inheritance:

   .. autoclass:: HTTPFactory
      :show-inheritance:
      :members:
