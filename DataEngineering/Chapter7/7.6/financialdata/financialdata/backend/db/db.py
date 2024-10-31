import typing

import pandas as pd
import pymysql
from loguru import logger
from sqlalchemy import engine,text

# 被upload_data呼叫
def update2mysql_by_pandas(
    df: pd.DataFrame,
    table: str,
    mysql_conn: engine.base.Connection,
):
    if len(df) > 0:
        try:
            df.to_sql(
                name=table,
                con=mysql_conn,
                if_exists="append",
                index=False,
                chunksize=1000,
            )
            # con = 已在transaction的sqlalchemy.engine.Connection物件時不會自動commit，需額外下Connection.commit()
            mysql_conn.commit()

        except Exception as e:
            logger.info(e)
            return False
    return True

# 被build_df_update_sql呼叫
def build_update_sql(
    colname: typing.List[str],
    value: typing.List[str],
):
    update_sql = ",".join(
        [
            ' `{}` = "{}" '.format(
                colname[i],
                str(value[i]),
            )
            for i in range(len(colname))
            if str(value[i])
        ]
    )
    return update_sql

# 被update2mysql_by_sql呼叫
def build_df_update_sql(
    table: str,
    df: pd.DataFrame
) -> typing.List[str]:
    logger.info("build_df_update_sql")
    df_columns = list(df.columns)
    sql_list = []
    for i in range(len(df)):
        temp = list(df.iloc[i])
        value = [
            pymysql.converters.escape_string(
                str(v)
            )
            for v in temp
        ]
        sub_df_columns = [
            df_columns[j]
            for j in range(len(temp))
        ]
        update_sql = build_update_sql(
            sub_df_columns, value
        )
        # SQL 上傳資料方式
        # DUPLICATE KEY UPDATE 意思是
        # 如果有重複，就改用 update 的方式
        # 避免重複上傳
        sql = """INSERT INTO `{}`({})VALUES ({}) ON DUPLICATE KEY UPDATE {}
            """.format(
            table,
            "`{}`".format(
                "`,`".join(
                    sub_df_columns
                )
            ),
            '"{}"'.format(
                '","'.join(value)
            ),
            update_sql,
        )
        sql_list.append(sql)
    return sql_list

# 被upload_data呼叫
def update2mysql_by_sql(
    df: pd.DataFrame,
    table: str,
    mysql_conn: engine.base.Connection,
):
    sql = build_df_update_sql(table, df)
    commit(
        sql=sql, mysql_conn=mysql_conn
    )


def commit(
    sql: typing.Union[
        str, typing.List[str]
    ],
    mysql_conn: engine.base.Connection = None,
):
    logger.info("commit")

    trans = None  # 確保Transaction有啟動
    try:
        if mysql_conn.in_transaction():
            logger.info("Transaction already in progress.")
            trans = mysql_conn
        else:
            trans = mysql_conn.begin()

        if isinstance(sql, list):
            for s in sql:
                try:
                    # SQL rawstring轉換成sqlalchemy textclause
                    s = text(s) if isinstance(s, str) else s
                    mysql_conn.execution_options(
                        autocommit=False
                    ).execute(s)
                # SQL語法執行出錯時，印出錯誤訊息以及出錯的SQL，用raise中斷程式觸發rollback
                except Exception as e:
                    logger.info(e)
                    logger.info(s)
                    raise

        elif isinstance(sql, str):
            # SQL rawstring轉換成sqlalchemy textclause
            sql = text(sql)
            mysql_conn.execution_options(
                autocommit=False
            ).execute(sql)
        
        # 在上述所有SQL執行成功後才commit
        trans.commit()
    
    # 出錯時，若Transaction進行中，則以trans.rollback()強制rollback，並用raise中斷程式
    except Exception as e:
        if trans is not None:
            trans.rollback()
        logger.info(e)
        raise

# 由task.py呼叫
def upload_data(
    df: pd.DataFrame,
    table: str,
    mysql_conn: engine.base.Connection,
):
    # 如果有爬到資料，嘗試上傳資料
    if len(df) > 0:
        # 先直接用df.to_sql()上傳
        if update2mysql_by_pandas(
            df=df,
            table=table,
            mysql_conn=mysql_conn,
        ):
            pass
        # 如果直接上傳失敗(可能有duplicate primary key)，改執行SQL語法更新
        else:
            update2mysql_by_sql(
                df=df,
                table=table,
                mysql_conn=mysql_conn,
            )
