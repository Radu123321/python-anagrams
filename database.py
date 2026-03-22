from sqlalchemy import create_engine, Column, Integer, String, Index, event, DDL, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./anagrams.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Word(Base):
    __tablename__ = "words" #private
    id = Column(Integer, primary_key=True, index=True)
    original_word = Column(String, nullable=False)
    sorted_word = Column(String, nullable=False)
    last_accessed = Column(DateTime, default = func.now(), onupdate=func.now())#cand a fost "atins" ultima oara
    #index(B-tree pentru performanta)
    __table_args__ = (
        Index('idx_sorted_word', 'sorted_word'),
        Index('idx_unique_word', 'original_word', unique=True),
    )

#Trigger(prinde cuvantul inainte sa fie salvat, creeaza o copie)
@event.listens_for(Word, 'before_insert')
def receive_before_insert(mapper, connection, target):
    target.original_word = target.original_word.lower().strip()
    target.sorted_word = "".join(sorted(target.original_word))

Base.metadata.create_all(bind=engine)