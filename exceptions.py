class StatusCodeError(Exception):
    """Исключение, если вернувшийся статус не 200."""

    pass


class UnknownStatusHomeWork(Exception):
    """Исключение, если неизвестный статус ДЗ."""

    pass
