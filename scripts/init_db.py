from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sql_dost.demo_data import initialize_database
from sql_dost.config import settings
if __name__ == "__main__":
    print("Initialized synthetic demo database:", initialize_database(settings.database_path, settings.schema_path))
