class NotAuthenticated(Exception):
    """Исключение, если недействительный или некорректный токен."""

    pass


class UnknownError(Exception):
    """Исключение передаваемых параметров.
    Если в запросе будет передано что-то неожиданное для сервиса.
    """

    pass