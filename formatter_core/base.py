from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any

class FormatDirection(Enum):
    FORMAT = "format"
    UNFORMAT = "unformat"

class BaseFormatter(ABC):
    @abstractmethod
    def format_code(self, code: str, **kwargs) -> Optional[str]:
        pass
        
    @abstractmethod
    def unformat_code(self, code: str, **kwargs) -> Optional[str]:
        pass

class BaseCodeProcessor(ABC):
    @abstractmethod
    def process(self, code: str, **kwargs) -> Optional[str]:
        pass