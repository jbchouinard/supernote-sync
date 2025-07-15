import datetime
from typing import List

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from snsync.config import Config
from snsync.schema import LocalFileMeta


class Base(DeclarativeBase):
    pass


class DbFileMeta(Base):
    __tablename__ = "file_meta"

    device_name: Mapped[str] = mapped_column(primary_key=True)
    device_path: Mapped[str] = mapped_column(primary_key=True)
    size: Mapped[int]
    md5: Mapped[bytes]
    last_synced: Mapped[datetime.datetime]
    last_sync_action: Mapped[str]

    @property
    def file_key(self):
        return (self.device_name, self.device_path.lstrip("/"))


_engines = {}


def get_engine(conf: Config) -> Engine:
    url = conf.db_url
    if url not in _engines:
        _engines[url] = create_engine(url)
    return _engines[url]


def get_session(conf: Config) -> Session:
    return Session(get_engine(conf))


def create_tables(conf: Config):
    engine = get_engine(conf)
    Base.metadata.create_all(bind=engine)


def get_db_files_meta(conf: Config) -> List[DbFileMeta]:
    session: Session
    with get_session(conf) as session:
        return session.query(DbFileMeta).filter_by(device_name=conf.supernote_device_name).all()


def delete_file_meta(file_key: tuple[str, str], conf: Config):
    session: Session
    with get_session(conf) as session:
        session.delete(
            session.query(DbFileMeta).filter_by(device_name=file_key[0], device_path=file_key[1]).one_or_none()
        )
        session.commit()


def record_file_action(meta: LocalFileMeta, action: str, conf: Config):
    session: Session
    with get_session(conf) as session:
        session.merge(
            DbFileMeta(
                device_name=meta.device_name,
                device_path=meta.file_key[1],
                size=meta.size,
                md5=meta.md5(),
                last_synced=datetime.datetime.now(),
                last_sync_action=action,
            )
        )
        session.commit()
