import logging
import os
import time
import telegram
import requests
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import StatusCodeError, ResponseException

load_dotenv()
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger: logging.Logger = logging.getLogger(__name__)

PRACTICUM_TOKEN: str = os.getenv('YAPRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TGBOT_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('MY_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


ACTUAL_STATUS: str = ''
HOMEWORK_VERDICTS: dict[str, str] = {
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
    if (
        PRACTICUM_TOKEN is None
        or TELEGRAM_TOKEN is None
        or TELEGRAM_CHAT_ID is None
    ):
        message = 'Отсутствуют обязательные переменные.'
        logger.critical(message)
        raise TypeError(message)


def send_message(bot: telegram.bot.Bot, message: str or None) -> None:
    """
    Отправляет сообщение в Telegram чат.
    Чат оперделяется переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения.
    """
    try:
        if message is not None:
            bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message
            )
            logger.debug('Сообщение отправлено')
    except Exception as error:
        logger.error(f'Сообщение не отправлено. {error}')


def get_api_answer(timestamp: int) -> dict or None:
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


def check_response(response: dict) -> bool or None:
    """
    Проверяет ответ API на соответствие документации.
    В качестве параметра функция получает ответ API,
    приведенный к типам данных Python.
    """
    if type(response) != dict:
        raise TypeError('Ожидаемый тип данных для response: dict')
    if type(response.get('homeworks')) != list:
        raise TypeError('Ожидаемый тип данных для homeworks: list')
    if len(response.get('homeworks')) == 0:
        raise TypeError('Отсутствуют данные о домашней работе')
    return True


def parse_status(homework: dict) -> str or None:
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент
    из списка домашних работ. В случае успеха, функция
    возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS
    """
    global ACTUAL_STATUS
    if homework.get('homework_name') is None:
        raise TypeError('В ответе отсутствует ключ homework_name')
    if not (homework.get('status') in HOMEWORK_VERDICTS.keys()):
        raise TypeError(
            'Получен неизвестный статус домашней работы'
        )

    if homework.get('status') != ACTUAL_STATUS:
        ACTUAL_STATUS = homework.get('status')
        return (
            f'Изменился статус проверки работы '
            f'"{homework.get("homework_name")}". '
            f'{HOMEWORK_VERDICTS[homework.get("status")]}'
        )


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot: telegram.bot.Bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = int(time.time())

    while True:
        try:
            response: dict = get_api_answer(timestamp)
            if check_response(response):
                result = parse_status(
                    response.get('homeworks')[0]
                )
                send_message(bot, result)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
