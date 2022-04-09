import logging

import numpy
import secrets

from aiogram import *
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State

from data import db_session
from data.company import Company
from data.meetings import Meetings
from data.staff import Staff
from secret import token

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
                         '/newtoken - получить новый токен компании\n'
                         '/delete_company - удаление компании')


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
    db_sess = db_session.create_session()
    db_sess.add(Company(name_company=data['name_company'],
                        token=token_company, hr=message.from_user.username))
    db_sess.commit()
    await state.finish()
    await message.answer("Организация создана\nТокен для приглашения")
    await message.answer(token_company)


class ConnectCompany(StatesGroup):
    connect = State()


@dp.message_handler(commands="connectcompany", state="*")
async def start_state(message):
    await message.answer(text='Напишите токен компании для подключения к ней')
    await ConnectCompany.connect.set()


@dp.message_handler(state=ConnectCompany.connect, content_types=types.ContentTypes.TEXT)
async def con_company(message, state: FSMContext):
    await state.update_data(connect=message.text.title())
    data = await state.get_data()
    db_sess = db_session.create_session()
    req = db_sess.query(Company).filter(Company.token.like(data['connect'])).first()
    if not req is None:
        db_sess.add(Staff(name=message.from_user.username, id_company=req.id))
        db_sess.commit()
    else:
        await message.reply("Компании с таким токеном не существует, попробуйте ещё раз")
        return
    await state.finish()
    await message.answer("Вы подключились к компании")
    await message.answer(req.name_company)


@dp.message_handler(commands="meet")
async def meetings(message):
    db_sess = db_session.create_session()
    first_per = db_sess.query(Staff).filter(Staff.name == message.from_user.username).first()
    id_1, id_com_1 = first_per.id, first_per.id_company
    if not first_per is None:
        second_per = (() for i in db_sess.query(Staff).filter(Staff.id_company == id_com_1).all())
        print(second_per)
        if len(second_per) > 0:
            await message.answer('Секунду я подбираю вам нового знакомого :)')
            print(db_sess.query(Meetings).filter().first())
            meets = db_sess.query(Meetings).filter((Meetings.id_first == id_com_1) | (Meetings.id_second == id_com_1)).all()
            meets = ((i.id_first, i.id_second) for i in meets)
            meet_per = numpy.fromiter((i for i in second_per if (i, id_1) not in meets
                                       and (id_1, i) not in meets and id_1 != i), dtype=int, count=1)
            if list(meet_per) is None:
                meet_per = db_sess.query(Staff).filter(Staff.id == list(meet_per)[0]).first()
                db_sess.add(Meetings(id_first=id_1, id_second=meet_per.id))
                db_sess.commit()
                await message.answer("Ваш новый знакомый")
                await message.answer(meet_per.name)
            else:
                await message.answer('Вы уже познакомились со всеми')
        else:
            await message.answer('В вашей компании нету сотрудников')


@dp.message_handler(commands="newtoken")
async def start_state(message):
    db_sess = db_session.create_session()
    token_company = secrets.token_urlsafe(16)
    company = db_sess.query(Company).filter(Company.hr == message.from_user.username).first()
    company.token = token_company
    db_sess.commit()
    await message.answer("Токен обновлен")
    await message.answer(token_company)


@dp.message_handler(commands=['exit_company'])
async def exit_company(message):
    db_sess = db_session.create_session()
    db_sess.query(Staff).filter(Staff.name == message.from_user.username).delete()
    db_sess.commit()
    await message.answer('Вы покинули компанию')


@dp.message_handler(commands=['delete_company'])
async def delete_company(message):
    db_sess = db_session.create_session()
    hr = db_sess.query(Company).filter(Company.hr == message.from_user.username).all()
    if hr:
        hr = hr[0].name_company
        db_sess.query(Staff).filter(Staff.id_company == hr).delete()
        db_sess.query(Company).filter(Company.name_company == hr).delete()
        db_sess.commit()
        await message.answer('Вы удалили свою компанию')
    else:
        await message.answer('У вас нету компаний')


if __name__ == '__main__':
    db_session.global_init("db/teambot.db")
    executor.start_polling(dp, skip_updates=True)
