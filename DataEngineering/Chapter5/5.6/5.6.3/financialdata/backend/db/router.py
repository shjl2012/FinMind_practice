import time
import typing

from loguru import logger
from sqlalchemy import engine,text,select
from financialdata.backend.db import clients


def check_alive(
    connect: engine.base.Connection,
):
    # 在每次使用之前，先確認 connect 是否活者
    # connect.execute("SELECT 1 + 1")
    # Updated syntax for sqlalchemy 2.0.31
    query = select(text("1 + 1"))
    connect.execute(query)


def check_connect_alive(
    connect: engine.base.Connection,
    connect_func: typing.Callable,
):
    if connect:
        try:
            check_alive(connect)
            return connect
        except Exception as e:
            logger.info(
                f"""
                {connect_func.__name__} reconnect, error: {e}
                """
            )
            time.sleep(1)
            try:
                connect = connect_func()
            except Exception as e:
                logger.info(
                    f"""
                    {connect_func.__name__} connect error, error: {e}
                    """
                )
            return check_connect_alive(
                connect, connect_func
            )


class Router:
    def __init__(self):
        self._mysql_financialdata_conn = (
            clients.get_mysql_financialdata_conn()
        )

    def check_mysql_financialdata_conn_alive(
        self,
    ):
        self._mysql_financialdata_conn = check_connect_alive(
            self._mysql_financialdata_conn,
            clients.get_mysql_financialdata_conn,
        )
        return (
            self._mysql_financialdata_conn
        )

    @property
    def mysql_financialdata_conn(self):
        return (
            self.check_mysql_financialdata_conn_alive()
        )

    def close_connection(self):
        self._mysql_financialdata_conn.close()
