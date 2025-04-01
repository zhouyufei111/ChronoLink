from datetime import date, datetime, time, timedelta, timezone
import json
import logging
from typing import Any, Union, List, Tuple
from openai import BaseModel
import pandas as pd
from mysql.connector import connection

from utils.constants import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD
# 设置日志记录器
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

RDS_HOST = MYSQL_HOST
RDS_PORT = MYSQL_PORT
RDS_USERNAME = MYSQL_USER
RDS_PASSWORD = MYSQL_PASSWORD


def serializable(
    input: Any,
) -> Union[list, dict, tuple, str, bytes, int, float, bool, None]:
    """Warning: the returned object will be a combination of list and dict or
    basic data types: str, int, float, bool.  Class objects will be represented
    as dict
    """
    if input is None:
        return None
    if isinstance(input, (str, int, float, bool)):
        return input
    if isinstance(input, bytes):
        try:
            return input.decode()
        except Exception:
            return ""
    if isinstance(input, datetime):
        return input.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(input, date):
        return input.strftime("%Y-%m-%d")
    if isinstance(input, time):
        return input.strftime("%H:%M:%S")
    if isinstance(input, (timedelta, timezone)):
        return str(input)
    if isinstance(input, (list, tuple)):
        output = []
        for item in input:
            output.append(serializable(item))
        return output
    if isinstance(input, dict):
        output = {}
        for k, v in input.items():
            output[k] = serializable(v)
        return output
    if isinstance(input, BaseModel):
        return serializable(input.dict())
    # For any other objects, if it has __dict__ attribute, then serialize
    try:
        return serializable(input.__dict__)
    except (AttributeError, SyntaxError):
        try:
            return str(input)
        except Exception:
            pass

class SQLConnector:
    def __init__(
        self,
        host: str = RDS_HOST,
        port: int = 3306,
        user: str = RDS_USERNAME,  # 默认MySQL用户名
        password: str = RDS_PASSWORD,  # 您的MySQL密码
        database: str = "",
        verbose=0,
    ):
        self.conn, self.cursor = None, None
        self.database = database if database else None
        self.verbose = verbose
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def _get_host(self, host: str = "", port: int = None):
        rds_host = host if host else RDS_HOST
        logger.info(f"Retrieved RDS_HOST from env variable: {rds_host}")
        if not rds_host:
            rds_host = "localhost:3306"
            logger.warning(f"Env variable RDS_HOST not found, set RDS host to default: {rds_host}")
        else:
            res = rds_host.split(":")
            self.host = res[0]
            if len(res) == 2:
                self.port = int(res[1])
                logger.info(f"RDS_PORT {port if port else RDS_PORT} will be ignored as host already include port")
            elif len(res) == 1:
                self.port = int(port if port else RDS_PORT)
            else:
                raise ValueError(f"Error in RDS_HOST input or format: {rds_host}")
            logger.info(f"Using RDS host: {self.host} on port {self.port}")

    def _get_credential(self, user: str = "", password: str = ""):
        self.user = user if user else RDS_USERNAME
        self.password = password if password else RDS_PASSWORD

    def get_connection(self):
        self._get_connection()

    def _get_connection(self):
        self.conn = connection.MySQLConnection(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
        )
        self.cursor = self.conn.cursor()
        return self.conn, self.cursor

    def _close_connection(self):
        if self.cursor:
            try:
                self.cursor.close()
            except AttributeError:
                pass
        if self.conn:
            self.conn.commit()
            try:
                self.conn.close()
            except AttributeError:
                pass
        self.conn, self.cursor = None, None

    def __enter__(self):
        if not self.conn or not self.cursor:
            self._get_connection()
        return self.cursor

    def __exit__(self, type, value, traceback):
        self._close_connection()

    def query(self, query: str):
        """Send a SQL query and obtain the data in batch
        Args:
            query: SQL query string
        Returns:
            (data, names)
        """
        if not self.conn or not self.conn.is_connected() or not self.cursor:
            self._get_connection()
        if self.cursor:
            try:
                self.cursor.execute(query)
                data = self.cursor.fetchall()
            except Exception as e:
                logger.error(f"Query not successful: {e}\tquery = {query[:500]}")
                return None, None
            logger.info("Query completed successfully.")

            names = self.cursor.description
            return data, names
        else:
            logger.error("Query not successful due to no active cursor.")
            return None, None

    def execute(self, query: str, fetchall=False, multi=False, commit=True) -> bool:
        if not self.conn or not self.conn.is_connected() or not self.cursor:
            self._get_connection()
        try:
            self.cursor.execute(query)
            if commit:
                self.conn.commit()
            if fetchall:
                return self.cursor.fetchall()
            return True
        except Exception as e:
            logger.error(f"DB query not successful: {e}\tquery = {query[:500]}")
            return False

    @staticmethod
    def repr_for_sql(s):
        if s is None:
            return "NULL"
        if isinstance(s, (dict, list)):
            if s:
                try:
                    s = json.dumps(serializable(s))
                except Exception:
                    logger.error(f"Error during JSON serialization of input data structure: {s}")
                    return "NULL"
            else:
                return "NULL"
        s_ = repr(s)
        if s_[0] == '"' and s_[-1] == '"':
            return s_.replace("'", r"\'").replace('"', "'")
        else:
            return s_

    def insert_data(
        self,
        table_name: str,
        data,
        columns: Union[List, Tuple] = None,
        return_query_only: bool = False,
        verbose=None,
    ) -> Union[bool, str]:
        if not self.conn or not self.conn.is_connected() or not self.cursor:
            self._get_connection()
        if not self.cursor or not self.conn:
            logger.error("No active connection or cursor.")
            return False
        insert_query = (
            "INSERT INTO {table} ({columns}) "
            "VALUES {data} ON DUPLICATE KEY UPDATE "
            "title=VALUES(title), summary=VALUES(summary), manual_hot_score=VALUES(manual_hot_score), "
            "auto_hot_score=VALUES(auto_hot_score), start_time=VALUES(start_time), end_time=VALUES(end_time), id_list=VALUES(id_list), "
            "time_list=VALUES(time_list), ticker=VALUES(ticker), tag1=VALUES(tag1), tag2=VALUES(tag2), tag3=VALUES(tag3), "
            "cluster_embedding=VALUES(cluster_embedding), emb_list=VALUES(emb_list)"
        )
        columns = ",".join(columns)
        insert_query = insert_query.format(table=table_name, columns=columns, data=data)
        try:
            self.cursor.execute(insert_query)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting data into table: {e}\n{insert_query}\n{data}")
            return False
        logger.info(f"Successfully inserted data into Table: {table_name}")
        return True

    def insert_failed_data(
        self,
        table_name: str,
        data,
        columns: Union[List, Tuple] = None,
        return_query_only: bool = False,
        verbose=None,
    ) -> Union[bool, str]:
        if not self.conn or not self.conn.is_connected() or not self.cursor:
            self._get_connection()
        if not self.cursor or not self.conn:
            logger.error("No active connection or cursor.")
            return False
        insert_query = "INSERT INTO {table} ({columns}) VALUES {data}"

        columns = ",".join(columns)
        insert_query = insert_query.format(table=table_name, columns=columns, data=data)
        try:
            self.cursor.execute(insert_query)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting data into table: {e}\n{insert_query}\n{data}")
            return False
        logger.info(f"Successfully inserted data into Table: {table_name}")
        return True

    def read_to_df(self, query):
        if not self.conn or not self.conn.is_connected() or not self.cursor:
            self._get_connection()
        if not self.cursor or not self.conn:
            logger.error("No active connection or cursor.")
            return False

        df = pd.read_sql(query, self.conn)

        return df

    def insert_data_into_table(
        self,
        table_name: str,
        data: Union[List, Tuple],
        columns: Union[List, Tuple] = None,
        return_query_only: bool = False,
        verbose=None,
    ) -> Union[bool, str]:
        if not self.conn or not self.conn.is_connected() or not self.cursor:
            self._get_connection()
        if not self.cursor or not self.conn:
            logger.error("No active connection or cursor.")
            return False
        if isinstance(data, pd.DataFrame):
            assert data.values is not None
            is_dataframe = True
        elif isinstance(data, (list, tuple)):
            assert columns is not None, "Need explicit columns names of data if not in DataFrame format"
            is_dataframe = False
        else:
            assert False, "Data format unrecognized."

        insert_query = "INSERT INTO {table} ({columns}) VALUES {values};"
        if is_dataframe:
            columns = ",".join(data.columns.tolist())  # Column names
            # values should eventually be like: "(....), (...), (...)"
            values = ["(" + ",".join(map(self.repr_for_sql, row)) + ")" for row in data.values]
            values = ", ".join(values)
            values = values.replace("None", "NULL")
        else:
            columns = ",".join(columns)
            # values = ["(" + ",".join(map(self.repr_for_sql, row)) + ")" for row in data]
            values = "('" + "','".join(data) + "')"
            # values = ", ".join(values)
            values = values.replace("None", "NULL")

        # for row in data.to_dict(orient="records"):
        # values = ",".join(map(repr, row.values()))
        insert_query = insert_query.format(table=table_name, columns=columns, values=values)

        # logger.debug("insert_query: %s\n" % insert_query)
        if return_query_only:
            logger.info(f"Successfully returned query for inserting data into Table: {table_name}")
            return insert_query
        try:
            self.cursor.execute(insert_query)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting data into table: {e}\n{insert_query}\n{data}")
            return False
        logger.info(f"Successfully inserted data into Table: {table_name}")
        return True

    def insert_data2(
        self,
        insert_query,
        columns: Union[List, Tuple] = None,
        return_query_only: bool = False,
        verbose=None,
    ) -> Union[bool, str]:
        if not self.conn or not self.conn.is_connected() or not self.cursor:
            self._get_connection()
        if not self.cursor or not self.conn:
            logger.error("No active connection or cursor.")
            return False
        try:
            self.cursor.execute(insert_query)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting data into table: {e}\n{insert_query}")
            print(f"Error inserting data into table: {e}\n")
            return False
        logger.info(f"Successfully inserted data into Table")
        print(f"Successfully inserted data into Table")
        return True
