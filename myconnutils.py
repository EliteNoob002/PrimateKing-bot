import mysql.connector
from bestconfig import Config
from mysql.connector import pooling
from mysql.connector import Error

config = Config() #config['version']

# Функция возвращает connection.
def getConnection(): 
    try:
        connection_pool = pooling.MySQLConnectionPool(pool_name="discord_pool",
                                                    pool_size=2,
                                                    pool_reset_session=True,
                                                    host=config['host'],
                                                    database=config['database'],
                                                    user=config['user'],
                                                    password=config['password'])

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