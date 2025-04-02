
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class Breaker(Base):
    __tablename__ = "breakers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Breaker")
    description = Column(String, default="")

    readings = relationship("PowerReading", back_populates="breaker")
    actions = relationship("BreakerAction", back_populates="breaker")

class PowerReading(Base):
    __tablename__ = "power_readings"

    id = Column(Integer, primary_key=True, index=True)
    breaker_id = Column(Integer, ForeignKey("breakers.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    power = Column(Float)
    voltage = Column(Float)
    current = Column(Float)

    breaker = relationship("Breaker", back_populates="readings")

class BreakerAction(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    breaker_id = Column(Integer, ForeignKey("breakers.id"))
    action = Column(String)
    source = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    breaker = relationship("Breaker", back_populates="actions")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)