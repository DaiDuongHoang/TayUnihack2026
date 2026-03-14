import importlib
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_database = importlib.import_module("database")
add_clothing_item = _database.add_clothing_item
get_user_catalog = _database.get_user_catalog
get_user_location = _database.get_user_location
get_user_profile = _database.get_user_profile
save_user_location = _database.save_user_location
