import psycopg2
from code.config import get_db_config

class Database:
    @staticmethod
    def get_connection():
        db_config = get_db_config()
        return psycopg2.connect(
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host']
        )

    @staticmethod
    def execute_query(query, params=None, fetch=False):
        conn = Database.get_connection()
        cur = conn.cursor()
        try:
            cur.execute(query, params)
            conn.commit()
            if fetch:
                return cur.fetchall()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def rebuild_db():
        query = '''
            DO $$ 
            DECLARE _tableName TEXT; 
            BEGIN 
                FOR _tableName IN SELECT tablename FROM pg_tables WHERE tablename LIKE 'group%' 
                LOOP 
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(_tableName) || ' CASCADE'; 
                END LOOP; 
            END; 
            $$;
            CREATE TABLE IF NOT EXISTS users_notifications (user_id BIGINT NOT NULL PRIMARY KEY, college VARCHAR(7) NOT NULL, checked BOOLEAN NOT NULL, 
                                                            user_group SMALLINT NOT NULL, time_notification VARCHAR(2) NOT NULL);
        '''
        Database.execute_query(query)
        
    @staticmethod
    def rebuild_group_table(group):
        query_drop = f'DROP TABLE IF EXISTS group_{group}'
        query_create = f'''
            CREATE TABLE group_{group} (
                week_day VARCHAR(2) NOT NULL,
                group_week_type BOOLEAN NOT NULL,
                group_data VARCHAR NOT NULL
            )
        '''
        Database.execute_query(query_drop)
        Database.execute_query(query_create)
