import asyncio
import logging
import re

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from environs import Env

from keyboards import get_menu_keyboard, generate_often_exchanges_keyboard

env = Env()
env.read_env()

dp = Dispatcher()


class APIError(Exception):
    def __init__(self, message):
        self.message = message


class CommandState(StatesGroup):
    state_often_exchange = State()


async def convert(amount: float, from_currency: str, to_currency: str) -> float:
    url = f'https://min-api.cryptocompare.com/data/price?fsym={from_currency}&tsyms={to_currency}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                raise RuntimeError(f'Incorrect response code: {response.status}')

            exchange = await response.json()

            if 'Response' in exchange:
                raise APIError(exchange['Message'])

    return exchange[to_currency] * amount


@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        text='Hello! I am a cryptocurrency conversion bot. Choose a command from the menu or press /help for assistance.',
        reply_markup=get_menu_keyboard(menu_buttons=menu_buttons))
    logger.info(f'User {message.from_user.id} has started the conversation.')


@dp.message(Command('help'))
async def help_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(text='Available commands:\n'
                              '/start - begin conversation with the bot\n'
                              '/help - get list of available commands\n'
                              '/convert <amount> <from_currency> <to_currency> - convert currency\n'
                              '/often_exchanges - display frequently requested conversions')
    logger.info(f'User {message.from_user.id} has requested help.')


@dp.message(Command('often_exchanges'))
async def often_exchanges_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    reply_markup = generate_often_exchanges_keyboard(often_exchanges)
    await message.answer(text='Frequently requested conversions today:', reply_markup=reply_markup)
    logger.info(f'User {message.from_user.id} has requested often exchanges.')


@dp.callback_query()
async def handle_callback(callback: CallbackQuery, state: FSMContext) -> None:
    from_currency, to_currency = callback.data.split()
    await state.update_data(from_currency=from_currency, to_currency=to_currency)
    message = callback.message
    await state.set_state(CommandState.state_often_exchange)
    await message.answer(text=f'You have selected exchange {from_currency} -> {to_currency}. Now enter the exchange amount')
    logger.info(f'User {callback.from_user.id} has selected exchange {from_currency} -> {to_currency}.')
    await callback.answer()

@dp.message(CommandState.state_often_exchange)
async def state_convert(message: Message, state: FSMContext) -> None:
    try:
        amount = float(message.text)
        state_data = await state.get_data()

        from_currency = state_data['from_currency']
        to_currency = state_data['to_currency']

        exchange_amount = await convert(amount, from_currency, to_currency)
        await message.answer(text=f'{amount} {from_currency} equals {round(exchange_amount, 5)} {to_currency}')
        await state.clear()

        logger.info(f'User {message.from_user.id} has completed the exchange successfully.')
    except ValueError as e:
        await message.answer(text='Please enter a number or begin again with /start')
        logger.error(f'User {message.from_user.id} attempted an invalid exchange amount. {e}')


@dp.message(Command('convert'))
async def convert_command(message: Message, command: CommandObject, state: FSMContext) -> None:
    await state.clear()
    try:
        parameters = command.args

        amount, from_currency, to_currency = parameters.split()

        amount = float(amount)
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        exchange_amount = await convert(amount, from_currency, to_currency)
        await message.answer(text=f'{amount} {from_currency} equals {round(exchange_amount, 5)} {to_currency}')

    except ValueError:
        await message.answer(text='Incorrect request format\n'
                                  'Use the template /convert <amount> <from_currency> <to_currency>\n'
                                  'Example: /convert 100 usd btc')
        logger.error(f'User {message.from_user.id} attempted an invalid conversion request.')
    except AttributeError as e:
        await message.answer(text='After /convert, use request attributes\n'
                                  'Use the template /convert <amount> <from_currency> <to_currency>\n'
                                  'Example: /convert 100 usd btc')
        logger.error(f'User {message.from_user.id} attempted an invalid conversion request. {e}')
    except RuntimeError as e:
        await message.answer(text='Failed to process the request. Please try again later')
        logger.error(f'User {message.from_user.id} encountered a runtime error during conversion. {e}')
    except APIError as e:
        await message.answer(text='Invalid request parameters or one of the selected currencies is not supported')
        logger.error(f'User {message.from_user.id} encountered an API error during conversion. {e}')


@dp.message(F.text)
async def hello_commands(message: Message) -> None:
    text = message.text.lower()
    match_greet = re.search(greetings, text)
    match_bye = re.search(goodbyes, text)
    if match_greet:
        await message.answer(text='Good day. This is a currency conversion bot.\n'
                                  'Press /help for details')
        logger.info(f'User {message.from_user.id} greeted the bot.')
    elif match_bye:
        await message.answer(text='Thank you for using our bot. Goodbye!')
        logger.info(f'User {message.from_user.id} bid farewell.')
    else:
        await message.answer(text='I do not understand you!\n'
                                  'Press /help for details')
        logger.warning(f'User {message.from_user.id} made an incomprehensible request.')


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    log_filename = env('LOG_FILENAME')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_filename)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    menu_buttons = ['/start', '/help', '/convert', '/often_exchanges']
    often_exchanges = ['BTC USD', 'ETH BTC', 'SOL USD', 'ETH USD', 'EUR RUB', 'USD RUB', 'RUB USD', 'USD EUR']

    greetings = r'hello|hi|hey|good morning|good afternoon|good evening'
    goodbyes = r'bye|goodbye|see you|farewell|have a nice day|good night'

    telegram_token = env('TELEGRAM_API_KEY')
    bot = Bot(telegram_token)

    asyncio.run(main())
