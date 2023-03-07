from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum, create_engine, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, joinedload


engine = create_engine("sqlite:///example.db") #, echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class MessageType(Enum):
    user_message = "user_message"
    user_command = "user_command"
    system = "system"
    bot_command_message = "bot_command_message"
    bot_message = "bot_message"

class UserMode(Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    phone_id = Column(String, unique=True)
    mode = Column(SQLAlchemyEnum(UserMode))

    @staticmethod
    def get_user(phone_id: str) -> Optional["User"]:
        with Session() as session:
            user = session.query(User).filter(User.phone_id == phone_id).first()
            return user

    @staticmethod
    def get_user_mode(phone_id: str) -> Optional[UserMode]:
        user = User.get_user(phone_id)
        if user:
            return user.mode
        return None

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    phone_id = Column(String)
    content = Column(String)
    timestamp = Column(DateTime)
    message_type = Column(SQLAlchemyEnum(MessageType))

    @staticmethod
    def add_message(
        phone_id: str, content: str, message_type: MessageType, timestamp: Optional[datetime] = None
    ) -> "Message":
        if timestamp is None:
            timestamp = datetime.now()
        with Session() as session:
            message = Message(phone_id=phone_id, content=content, timestamp=timestamp, message_type=message_type)
            session.add(message)
            session.commit()
            return message

    @staticmethod
    def update_user_mode(phone_id: str, mode: UserMode) -> None:
        with Session() as session:
            user = session.query(User).filter(User.phone_id == phone_id).first()
            if user:
                user.mode = mode
            else:
                user = User(phone_id=phone_id, mode=mode)
                session.add(user)
            session.commit()

    @staticmethod
    def get_most_recent_message(phone_id: str, before_timestamp: datetime) -> Optional["Message"]:
        with Session() as session:
            message = (
                session.query(Message)
                .filter(Message.phone_id == phone_id)
                .filter(Message.timestamp < before_timestamp)
                .order_by(desc(Message.timestamp))
                .first()
            )
            return message

    @staticmethod
    def get_last_n_messages(phone_id: str, n: int) -> List["Message"]:
        with Session() as session:
            messages = (
                session.query(Message)
                .filter(Message.phone_id == phone_id)
                .order_by(Message.timestamp.asc())
                .limit(n)
                .all()
            )
            return messages
        
# create tables if they don't exist
try:
    Base.metadata.create_all(engine)
except:
    # delete database and try again
    import os
    print("Deleting database and trying again")
    os.remove("example.db")
    Base.metadata.create_all(engine)
