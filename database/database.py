from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database configuration
DATABASE_URL = "postgresql://postgres:Unknown%40404@localhost:5432/sqlalchemy2"

# Create a database engine
engine = create_engine(DATABASE_URL, echo=True)

# Define a base class for models
Base = declarative_base()

# Create a sessionmaker bound to the engine
get_db = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the table
# Base.metadata.create_all(bind=engine)
