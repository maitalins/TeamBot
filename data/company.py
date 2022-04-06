import sqlalchemy


from .db_session import SqlAlchemyBase


class Company(SqlAlchemyBase):
    __tablename__ = 'company'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True, unique=True)
    name_company = sqlalchemy.Column(sqlalchemy.Integer)
    token = sqlalchemy.Column(sqlalchemy.String)
    hr = sqlalchemy.Column(sqlalchemy.String)
