from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config,pool
from app.core import Base
from app import models,advanced_models
config=context.config
if config.config_file_name:fileConfig(config.config_file_name)
target_metadata=Base.metadata
def offline():
 context.configure(url=config.get_main_option('sqlalchemy.url'),target_metadata=target_metadata,literal_binds=True);context.run_migrations()
def online():
 connectable=engine_from_config(config.get_section(config.config_ini_section),prefix='sqlalchemy.',poolclass=pool.NullPool)
 with connectable.connect() as connection:context.configure(connection=connection,target_metadata=target_metadata);context.run_migrations()
if context.is_offline_mode():offline()
else:online()
