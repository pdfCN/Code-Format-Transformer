from typing import Optional, Dict, Any
from .formatters import UncrustifyFormatter, PythonFormatter 

class LanguageSupport:
    SUPPORTED_LANGUAGES = {
        'java': {
            'extension': '.java',
            'processors': ['whitespace', 'comment'],
        },
        'cpp': {
            'extension': '.cpp',
            'processors': ['whitespace', 'comment'],
        },
        'csharp': {
            'extension': '.cs',
            'processors': ['whitespace', 'comment'],
        },
        'python': {
            'extension': '.py',
            'formatter': PythonFormatter,
        }
    }
    
    @classmethod
    def get_language_config(cls, language: str) -> Optional[Dict[str, Any]]:
        return cls.SUPPORTED_LANGUAGES.get(language)
        
    @classmethod
    def is_supported(cls, language: str) -> bool:
        return language in cls.SUPPORTED_LANGUAGES