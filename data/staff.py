import sqlalchemy
from sqlalchemy import orm

from db_session import SqlAlchemyBase


class Staff(SqlAlchemyBase):
    __tablename__ = 'staff'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True, unique=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    id_company = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('company.id'))

    id_comp = orm.relationship('Company')
