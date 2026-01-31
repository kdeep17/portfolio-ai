from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import pandas as pd

@dataclass
class MarketData:
    """
    Central repository for all external data.
    Populated once at the start of the pipeline.
    """
    info: Dict[str, Any] = field(default_factory=dict)
    financials: Dict[str, pd.DataFrame] = field(default_factory=dict)
    balance_sheet: Dict[str, pd.DataFrame] = field(default_factory=dict)
    news: Dict[str, List[Any]] = field(default_factory=dict)

    def get_info(self, symbol: str) -> dict:
        return self.info.get(symbol, {})

    def get_financials(self, symbol: str) -> Optional[pd.DataFrame]:
        return self.financials.get(symbol)

    def get_balance_sheet(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Retrieves the balance sheet dataframe for a given symbol.
        Returns None if data is missing.
        """
        return self.balance_sheet.get(symbol)
        
    def get_news(self, symbol: str) -> list:
        return self.news.get(symbol, [])