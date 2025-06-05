import datetime
from typing import Optional

from billwatcher.types import Language
from sqlalchemy import (
    DDL,
    DateTime,
    ForeignKey,
    create_engine,
    event,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    scoped_session,
    sessionmaker,
)
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class BillDocument(Base):
    __tablename__ = "bill_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"))


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[Optional[str]]
    file_source: Mapped[str]
    file_url: Mapped[Optional[str]]
    file_name: Mapped[Optional[str]]
    file_hash: Mapped[Optional[str]]
    file_id: Mapped[Optional[str]]
    processed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    bills = relationship("Bill", secondary="bill_documents", back_populates="documents")


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int]
    status: Mapped[str]
    document_source: Mapped[str]
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    documents = relationship(
        "Document", secondary="bill_documents", back_populates="bills"
    )


class BillData(Base):
    __tablename__ = "bill_datas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    language: Mapped[Language]
    content: Mapped[Optional[str]]
    content_tsv: Mapped[Optional[str]] = mapped_column(TSVECTOR())
    file_url: Mapped[Optional[str]]
    file_id: Mapped[Optional[str]]
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    bill = relationship("Bill", back_populates="datas")


context_tsv_ddl = DDL("""
CREATE INDEX content_tsv_idx ON bill_datas USING gin(content_tsv);
""")
event.listen(BillData.__table__, "after_create", context_tsv_ddl)


@event.listens_for(BillData, "before_insert")
@event.listens_for(BillData, "before_update")
def update_search_vector(mapper, connection, target):
    target.context_tsv = func.to_tsvector(target.content)


class BillTitle(Base):
    __tablename__ = "bill_titles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    title: Mapped[str]
    language: Mapped[Language]
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    bill = relationship("Bill", back_populates="titles")


class BillHistory(Base):
    __tablename__ = "bill_histories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("bills.id"))
    status: Mapped[str]
    date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    bill = relationship("Bill", back_populates="histories")


def connect_db(dsn: str) -> scoped_session[Session]:
    engine = create_engine(dsn)

    # Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    return scoped_session(sessionmaker(bind=engine))
