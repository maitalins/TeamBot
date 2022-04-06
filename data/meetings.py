import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Meetings(SqlAlchemyBase):
    __tablename__ = 'meetings'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True, unique=True)
    id_first = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('staff.id'))
    id_second = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('staff.id'))

    first = orm.relationship("Staff", foreign_keys=[id_first])
    second = orm.relationship("Staff", foreign_keys=[id_second])
