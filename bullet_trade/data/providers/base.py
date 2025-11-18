from abc import ABC, abstractmethod
from typing import Union, List, Optional, Dict, Any
from datetime import datetime
import pandas as pd


class DataProvider(ABC):
    """
    抽象数据提供者接口。
    不同数据源（jqdatasdk、tushare、miniqmt等）实现该接口，
    以便在框架内可插拔切换数据来源。
    """
    name: str = "base"
    # 是否要求实时行情必须由 provider 提供（用于 live 模式防止回落到历史数据）
    requires_live_data: bool = False

    def auth(self, user: Optional[str] = None, pwd: Optional[str] = None, host: Optional[str] = None, port: Optional[int] = None) -> None:
        """执行数据源认证或初始化。可选。默认读取环境变量，也可传入账号参数。"""
        pass

    @abstractmethod
    def get_price(
        self,
        security: Union[str, List[str]],
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        frequency: str = 'daily',
        fields: Optional[List[str]] = None,
        skip_paused: bool = False,
        fq: str = 'pre',
        count: Optional[int] = None,
        panel: bool = True,
        fill_paused: bool = True,
        pre_factor_ref_date: Optional[Union[str, datetime]] = None,
        prefer_engine: bool = False,
    ) -> pd.DataFrame:
        pass


    @abstractmethod
    def get_trade_days(
        self,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        count: Optional[int] = None
    ) -> List[datetime]:
        pass

    @abstractmethod
    def get_all_securities(
        self,
        types: Union[str, List[str]] = 'stock',
        date: Optional[Union[str, datetime]] = None
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_index_stocks(
        self,
        index_symbol: str,
        date: Optional[Union[str, datetime]] = None
    ) -> List[str]:
        pass

    @abstractmethod
    def get_split_dividend(
        self,
        security: str,
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None
    ) -> List[Dict[str, Any]]:
        pass

    def get_security_info(self, security: str) -> Dict[str, Any]:
        """
        返回指定标的的元信息，例如类型或子类型。
        默认返回空字典，可由具体数据提供者覆盖。
        """
        return {}
