import mysql.connector
from bestconfig import Config
from mysql.connector import pooling
from mysql.connector import Error
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("config.yaml")
config = Config(str(CONFIG_PATH))

def _get_cfg(key: str):
    try:
        return config[key]
    except KeyError:
        raise RuntimeError(f"В bestconfig-конфиге нет ключа '{key}'. Проверь файл конфигурации для БД.")

# Функция возвращает connection.
def getConnection(): 
    try:
        connection_pool = pooling.MySQLConnectionPool(
            pool_name="discord_pool",
            pool_size=2,
            pool_reset_session=True,
            host=_get_cfg('host_db'),
            database=_get_cfg('database'),
            user=_get_cfg('user_db'),
            password=_get_cfg('password_db'),
        )
        # Get connection object from a pool
        connection_object = connection_pool.get_connection()

        if connection_object.is_connected():
            db_Info = connection_object.get_server_info()
            print("Connected to MySQL database using connection pool ... MySQL Server version on ", db_Info)

            cursor = connection_object.cursor()
            cursor.execute("select database();")
            record = cursor.fetchone()
            print("Your connected to - ", record)
        else:
            connection_object.reconnect(attempts=1, delay=0)

    except Error as e:
        print("Error while connecting to MySQL using Connection pool ", e)
    return connection_object