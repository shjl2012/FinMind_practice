from pydantic import BaseModel
import importlib

import pandas as pd


class TaiwanStockPrice(BaseModel):
    StockID: str
    TradeVolume: int
    Transaction: int
    TradeValue: int
    Open: float
    Max: float
    Min: float
    Close: float
    Change: float
    Date: str


class TaiwanFuturesDaily(BaseModel):
    Date: str
    FuturesID: str
    ContractDate: str
    Open: float
    Max: float
    Min: float
    Close: float
    Change: float
    ChangePer: float
    Volume: float
    SettlementPrice: float
    OpenInterest: int
    TradingSession: str


# 被crawler.taiwan_futures_daily.py, crawler.taiwan_stock_price.py呼叫，功能如下

# 1. 把爬蟲爬到的資料轉換為dict物件df_dict
# 2. 動態匯入financialdata.schema.dataset中對應的class為schema
# 3. 針對df_dict內每個dictionary物件做資料類別轉換，如果df_dict內有資料型態無法被轉換、有多或缺少欄位時會噴轉換錯誤
# 4. 資料型態檢查/轉換完成後重新轉回dataframe回傳
def check_schema(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """檢查資料型態, 確保每次要上傳資料庫前, 型態正確"""
    df_dict = df.to_dict("records")
    schema = getattr(
        importlib.import_module("financialdata.schema.dataset"),
        dataset,
    )
    df_schema = [schema(**dd).__dict__ for dd in df_dict]
    # **dd => Argument unpacking
    # list comprehension本身沒有認證功能，是pydantic.BaseModel的功能在做資料型態認證，認證成功的資料會存在schema(**dd).__dict__中
    df = pd.DataFrame(df_schema)
    return df
