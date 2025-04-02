from db import Base, engine
import models
#init db testing
print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("Done.")
