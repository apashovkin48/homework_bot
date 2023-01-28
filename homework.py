import logging
import os
import time
import telegram
import requests
import sys
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import (
    StatusCodeError, ResponseException, TelegramSendMessageException
)

load_dotenv()
logger = logging.getLogger(__name__)

PRACTICUM_TOKEN = os.getenv('YAPRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TGBOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


ACTUAL_STATUS = ''
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_content_message():
    """
    Проверка на повторяемость результатов.
    Необходимо что бы бот постоянно не отправлял сообщения,
    а только по факту изменения
    """
    message = ['']

    def inner(args):
        """inner."""
        print(message, args)
        if message[0] != args:
            message[0] = args
            return message[0]
        return None

    return inner


def check_tokens() -> None:
    """
    Проверяет доступность переменных окружения.
    Если отсутствует хотя бы одна переменная окружения —
    продолжать работу бота нет смысла.
    """
    if (
        PRACTICUM_TOKEN is not None
        and TELEGRAM_TOKEN is not None
        and TELEGRAM_CHAT_ID is not None
    ):
        return
    logger.critical('Отсутствуют обязательные переменные.')
    sys.exit(0)


def send_message(bot, message) -> None:
    """
    Отправляет сообщение в Telegram чат.
    Чат оперделяется переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения.
    """
    try:
        if message is not None:
            logger.debug(f'Бот отправляет сообщение {message}')
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message
            )
            logger.debug('Сообщение отправлено')
    except telegram.TelegramError as error:
        message = f'Сообщение не отправлено. {error}'
        logger.error(message)
        raise TelegramSendMessageException(message)


def get_api_answer(timestamp):
    """
    Делает запрос к единственному эндпоинту API-сервиса.
    В качестве параметра в функцию передается временная метка.
    В случае успешного запроса должна вернуть ответ API,
    приведя его из формата JSON к типам данных Python.
    """
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={
                'from_date': timestamp
            }
        )
    except requests.RequestException as error:
        raise ResponseException(error)

    if homework_statuses.status_code == HTTPStatus.OK:
        return homework_statuses.json()
    else:
        raise StatusCodeError(
            f'Упс, возникла проблемка начальник. '
            f'Статус код: {homework_statuses.status_code}'
        )


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    """
    if not isinstance(response, dict):
        raise TypeError('Ожидаемый тип данных для response: dict')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Ожидаемый тип данных для homeworks: list')
    if len(response.get('homeworks')) == 0:
        raise TypeError('Отсутствуют данные о домашней работе')
    return True


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент
    из списка домашних работ. В случае успеха, функция
    возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS
    """
    if homework.get('homework_name') is None:
        raise TypeError('В ответе отсутствует ключ homework_name')
    if not (homework.get('status') in HOMEWORK_VERDICTS):
        raise TypeError(
            'Получен неизвестный статус домашней работы'
        )
    return (
        f'Изменился статус проверки работы '
        f'"{homework.get("homework_name")}". '
        f'{HOMEWORK_VERDICTS[homework.get("status")]}'
    )


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        format='%(asctime)s, %(levelname)s, %(message)s'
    )

    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    # test unix time 1674831185
    timestamp = int(time.time())
    message_content = check_content_message()

    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                result = parse_status(
                    response.get('homeworks')[0]
                )
                message = message_content(result)
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
