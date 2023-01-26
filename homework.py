import logging
import os
import requests
from dotenv import load_dotenv
from http import HTTPStatus
from telegram import Bot
from time import time, sleep
from pprint import pprint
from exceptions import UnknownError, NotAuthenticated

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)


PRACTICUM_TOKEN = os.getenv('YAPRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TGBOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_CHAT_ID')

RETRY_PERIOD: int = 6
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


ACTUAL_VERDICT = ''
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> None:
    """
    Проверяет доступность переменных окружения.
    Если отсутствует хотя бы одна переменная окружения —
    продолжать работу бота нет смысла.
    """
    if PRACTICUM_TOKEN is None:
        raise TypeError('Невозможно получить токен Яндекс Практикума.')
    if TELEGRAM_TOKEN is None:
        raise TypeError('Невозможно получить токен Telegram Бота')
    if TELEGRAM_CHAT_ID is None:
        raise TypeError('Невозможо получить уникальный Chat ID Telegram')


def send_message(bot, message) -> None:
    """
    Отправляет сообщение в Telegram чат.
    Чат оперделяется переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения.
    """
    if message is not None:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )


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

        if homework_statuses.status_code == HTTPStatus.OK:
            return homework_statuses.json()
        elif homework_statuses.status_code == HTTPStatus.BAD_REQUEST:
            raise NotAuthenticated(
                'Недействительный или некорректный токен Яндекс Практикума'
            )
        elif homework_statuses.status_code == HTTPStatus.UNAUTHORIZED:
            raise UnknownError(
                'В запросе передано что-то неожиданное для сервиса'
            )

    except UnknownError as error:
        logging.ERROR(error)
    except NotAuthenticated as error:
        logging.ERROR(error)


def check_response(response):
    """
    Проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    """
    if (
        response is not None
        and response.get('homeworks') is not None
        and response.get('current_date') is not None
        and len(response.get('homeworks')) > 0
    ):
        return True
    return False


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент
    из списка домашних работ. В случае успеха, функция
    возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS
    """
    global ACTUAL_VERDICT
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS[homework.get('status')]
    print(homework.get('status'), ACTUAL_VERDICT)
    if homework.get('status') != ACTUAL_VERDICT:
        ACTUAL_VERDICT = homework.get('status')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time())

    while True:
        try:
            response = get_api_answer(timestamp)
            correct_response = check_response(response)
            if correct_response:
                homework = response.get('homeworks')[0]
                result = parse_status(homework)
                send_message(bot, result)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            print(message)
            logging.ERROR(message)
        sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
