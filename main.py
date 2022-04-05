import logging

import numpy
import psycopg2
import secrets

from aiogram import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from secret import token, database

bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)


async def set_default_commands(dp):
    await dp.bot.set_my_commands([
        types.BotCommand("help", "Список команд"),
        types.BotCommand("helphr", "Список команд для hr"),
        types.BotCommand("connectcompany", "подключиться к компании"),
        types.BotCommand("meet", "создать встречу")
    ])


@dp.message_handler(commands='start')
async def start(message):
    await message.answer('Привет, меня зовут TeamBot и я помогу вам лучше узнать тех,'
                         ' с кем вы работаете, если вы конечно не HR :)')


@dp.message_handler(commands='help')
async def help(message):
    await message.answer('/connectcompany - подключиться к компании\n'
                         '/meet - создать встречу')


@dp.message_handler(commands='helphr')
async def helphr(message):
    await message.answer('/createcompany - создать компанию и получить '
                         'токен для подключения к компании\n'
                         '/newtoken - получить новый токен компании')


class CreateCompany(StatesGroup):
    name_company = State()


@dp.message_handler(commands="createcompany", state="*")
async def start_state(message):
    await message.answer(text='Напишите название организации')
    await CreateCompany.name_company.set()


@dp.message_handler(state=CreateCompany.name_company, content_types=types.ContentTypes.TEXT)
async def get_name_company(message, state: FSMContext):
    if any(map(str.isdigit, message.text)):
        await message.reply("Некорректное название, напишите еще раз")
        return
    await state.update_data(name_company=message.text.title())
    data = await state.get_data()
    token_company = secrets.token_urlsafe(16)
    con = psycopg2.connect(
        database=database['database'],
        user=database['user'],
        password=database['password'],
        host=database['host'],
        port=database['port']
    )
    cur = con.cursor()
    cur.execute(
        "INSERT INTO company (name_company, token, hr) "
        "VALUES (%s, %s, %s)", (data['name_company'], token_company, message.from_user.username))
    con.commit()
    con.close()
    await state.finish()
    await message.answer(f'Организация создана\nТокен для приглашения - {token_company}')


class ConnectCompany(StatesGroup):
    connect = State()


@dp.message_handler(commands="connectcompany", state="*")
async def start_state(message):
    await message.answer(text='Напишите токен компании для подключения к ней')
    await ConnectCompany.connect.set()


@dp.message_handler(state=ConnectCompany.connect, content_types=types.ContentTypes.TEXT)
async def con_company(message, state: FSMContext):
    if any(map(str.isdigit, message.text)):
        await message.reply("Некорректный токен, напишите еще раз")
        return
    await state.update_data(connect=message.text.title())
    data = await state.get_data()
    con = psycopg2.connect(
        database=database['database'],
        user=database['user'],
        password=database['password'],
        host=database['host'],
        port=database['port']
    )
    cur = con.cursor()
    req = cur.execute(
        "SELECT id, name FROM company WHERE token = %s", (data['connect'],)).fetchone()
    if not req is None:
        cur.execute(
            "INSERT INTO staff (name, id_company) VALUES (%s, %s)",
            (message.from_user.username, req[0][0]))
        con.commit()
    else:
        await message.reply("Компании с таким токеном не существует, попробуйте ещё раз")
        return
    con.close()
    await state.finish()
    await message.answer(f'Вы подключились к компании - {req[0][1]}')


@dp.message_handler(commands="meet")
async def meetings(message):
    con = psycopg2.connect(
        database=database['database'],
        user=database['user'],
        password=database['password'],
        host=database['host'],
        port=database['port']
    )
    cur = con.cursor()
    id_1, id_com_1 = first_per = cur.execute("SELECT id, id_company FROM staff WHERE name = %s",
                                             (message.from_user.username,)).fetchone()
    if not first_per is None:
        second_per = cur.execute("SELECT id"
                                 "FROM staff WHERE id_company = %s", (id_com_1,)).fetchall()
        if len(second_per) > 0:
            await message.answer('Секунду я подбираю ##########')
            meets = cur.execute("SELECT id_first, id_second"
                                "FROM meetings WHERE "
                                "id_first = %s or id_second = %s",
                                (id_1, id_1)).fetchall()
            meet_per = numpy.fromiter((i for i in second_per if (i, id_1) not in meets
                                       and (id_1, i) not in meets and id_1 != i), dtype=int, count=1)
            if list(meet_per) is None:
                meet_per = cur.execute("SELECT id, name FROM staff WHERE id = %s",
                                       (list(meet_per)[0],)).fetchone()
                cur.execute(
                    "INSERT INTO meetings (id_first, id_second) VALUES (%s, %s)",
                    (id_1, meet_per[0]))
                con.commit()
                await message.answer(f'Ваш новый знакомый - {meet_per[1]}')
            else:
                await message.answer('Вы уже познакомились со всеми')
        else:
            await message.answer('В вашей компании нету сотрудников')
    con.close()


@dp.message_handler(commands="newtoken")
async def start_state(message):
    con = psycopg2.connect(
        database=database['database'],
        user=database['user'],
        password=database['password'],
        host=database['host'],
        port=database['port']
    )
    cur = con.cursor()
    token_company = secrets.token_urlsafe(16)
    cur.execute(
        'UPDATE company set token = %s where hr = %s',
        (token_company, message.from_user.username))
    con.commit()
    con.close()
    await message.answer(f'Токен обновлен - {token_company}')


@dp.message_handler(commands=['exit_company'])
def exit_company(message):
    con = psycopg2.connect(
        database=database['database'],
        user=database['user'],
        password=database['password'],
        host=database['host'],
        port=database['port']
    )
    cur = con.cursor()
    cur.execute('DELETE FROM staff where name = %s;', (message.from_user.username,))
    con.commit()
    con.close()
    message.answer('Вы покинули компанию')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
