# formatter_core/factory.py
from typing import Dict, Optional
from .base import BaseFormatter
class FormatterFactory:
    
    _formatters: Dict[str, BaseFormatter] = {}
    
    @classmethod
    def register_formatter(cls, language: str, formatter: BaseFormatter):
        cls._formatters[language] = formatter
        
    @classmethod
    def get_formatter(cls, language: str) -> Optional[BaseFormatter]:
        return cls._formatters.get(language)