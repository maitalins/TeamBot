import logging
from itertools import islice

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


async def check(message):
    if not message.from_user.username is None:
        pass
    else:
        await message.answer('У вас отсутствует никнейм')
        return None


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
    if await check(message) is None:
        return
    db_sess = db_session.create_session()
    req = db_sess.query(Company).filter(Company.hr.like(message.from_user.username)).first()
    if not req:
        await message.answer(text='Напишите название организации')
        await CreateCompany.name_company.set()
    else:
        await message.answer('У вас есть уже компания')


@dp.message_handler(state=CreateCompany.name_company, content_types=types.ContentTypes.TEXT)
async def get_name_company(message, state: FSMContext):
    if not any(map(str.isalnum, message.text)):
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
    if await check(message) is None:
        return
    await message.answer(text='Напишите токен компании для подключения к ней')
    await ConnectCompany.connect.set()


@dp.message_handler(state=ConnectCompany.connect, content_types=types.ContentTypes.TEXT)
async def con_company(message, state: FSMContext):
    if await check(message) is None:
        return
    await state.update_data(connect=message.text.title())
    data = await state.get_data()
    db_sess = db_session.create_session()
    hr = db_sess.query(Company).filter(Company.hr.not_like(message.from_user.username)).first()
    if not hr is None:
        req = db_sess.query(Company).filter(Company.token.like(data['connect'])).first()
        if not req is None:
            db_sess.add(Staff(name=message.from_user.username, id_company=req.id))
            db_sess.commit()
            await state.finish()
            await message.answer("Вы подключились к компании")
            await message.answer(req.name_company)
        else:
            await message.reply("Компании с таким токеном не существует, попробуйте ещё раз")
            return
    else:
        await message.answer('Вы управляете компанией')
        return


@dp.message_handler(commands="meet")
async def meetings(message):
    if await check(message) is None:
        return
    db_sess = db_session.create_session()
    hr = db_sess.query(Company).filter(Company.hr.not_like(message.from_user.username)).first()
    if not hr is None:
        first_per = db_sess.query(Staff).filter(Staff.name.like(message.from_user.username)).first()
        hr = db_sess.query(Company).filter(Company.hr.not_like(message.from_user.username)).first()
        if not first_per is None:
            id_1, id_com_1 = first_per.id, first_per.id_company
            second_per = db_sess.query(Staff).filter(Staff.id_company == id_com_1).all()
            if len(second_per) > 0:
                await message.answer('Секунду я подбираю вам нового знакомого :)')
                meets = db_sess.query(Meetings).filter((Meetings.id_first.like(id_1)) | (Meetings.id_second.like(id_1))).all()
                meets = tuple((i.id_first, i.id_second) for i in meets)
                try:
                    meet_per = list(islice(filter(lambda x: (x.id, id_1) not in meets and (id_1, x.id)
                                                                not in meets and id_1 != x.id, second_per), 1))
                    if meet_per:
                        person = db_sess.query(Staff).filter(Staff.id == meet_per[0].item()).first()
                        db_sess.add(Meetings(id_first=id_1, id_second=person.id))
                        db_sess.commit()
                        await message.answer("Ваш новый знакомый")
                        await message.answer(f'@{person.name}')
                    else:
                        await message.answer('Вы уже познакомились со всеми')
                except Exception:
                    await message.answer('Вы уже познакомились со всеми или в компании отсутствуют ваши коллеги')
            else:
                await message.answer('В вашей компании нету сотрудников')
        else:
            await message.answer('Вы не состоите в компании')
    else:
        await message.answer('Вы hr, вам нельзя знакомиться :)')


@dp.message_handler(commands="newtoken")
async def start_state(message):
    if await check(message) is None:
        return
    db_sess = db_session.create_session()
    token_company = secrets.token_urlsafe(16)
    company = db_sess.query(Company).filter(Company.hr == message.from_user.username).first()
    if not company is None:
        company.token = token_company
        db_sess.commit()
        await message.answer("Токен обновлен")
        await message.answer(token_company)
    else:
        await message.answer('У вас нет компании')


@dp.message_handler(commands=['exit_company'])
async def exit_company(message):
    if await check(message) is None:
        return
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
        await message.answer('У вас отсутствует компания')


if __name__ == '__main__':
    db_session.global_init("db/teambot.db")
    executor.start_polling(dp, skip_updates=True)
