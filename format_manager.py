# format_manager.py

import os
import logging
from typing import Optional
from formatter_core.base import FormatDirection, BaseFormatter
from formatter_core.factory import FormatterFactory
from formatter_core.formatters import UncrustifyFormatter, PythonFormatter
from formatter_core.language_support import LanguageSupport
from formatter_core.processors import WhitespaceProcessor, CommentProcessor

class CodeFormatManager:
    def __init__(self, config_dir: str = "cfg"):
        # Create log directory
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Configuration log
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                # File processor
                logging.FileHandler(os.path.join(log_dir, 'format_manager.log')),
                # Console processor
                # logging.StreamHandler()
            ]
        )

        self.config_dir = config_dir
        self._initialize_formatters()
        self.whitespace_processor = WhitespaceProcessor()
        self.comment_processor = CommentProcessor()
            
    def _initialize_formatters(self):
        uncrustify = UncrustifyFormatter(self.config_dir)
        
        for language in LanguageSupport.SUPPORTED_LANGUAGES:
            if language == 'python':
                FormatterFactory.register_formatter('python', PythonFormatter())
            else:
                FormatterFactory.register_formatter(language, uncrustify)
            
    def _get_formatter(self, language: str) -> Optional[BaseFormatter]:
        if not LanguageSupport.is_supported(language):
            logging.error(f"Unsupported language: {language}")
            return None
        return FormatterFactory.get_formatter(language)
                
    def _process_code(self, code: str, language: str, direction: FormatDirection) -> Optional[str]:
        formatter = self._get_formatter(language)
        if not formatter:
            return None
            
        try:
            if direction == FormatDirection.FORMAT:
                processed_code = formatter.format_code(code, language=language)
            else:
                processed_code = formatter.unformat_code(code, language=language)
                if processed_code and language != 'python':
                    processed_code = self.whitespace_processor.process(
                        processed_code,
                        lang=language
                    )
                    processed_code = self.comment_processor.process(
                        processed_code, 
                        mode='preserve',
                        lang=language
                    )
            return processed_code
            
        except Exception as e:
            logging.error(f"Error processing code: {e}")
            return None
            
    def process_file(self, input_path: str, output_path: str, 
                    direction: FormatDirection) -> bool:
        try:
            if not os.path.exists(input_path):
                logging.error(f"Input file not found: {input_path}")
                return False

            if os.path.getsize(input_path) == 0:
                logging.error(f"Input file is empty: {input_path}")
                return False
                
            ext = os.path.splitext(input_path)[1].lower()
            language = None
            
            for lang, config in LanguageSupport.SUPPORTED_LANGUAGES.items():
                if config['extension'] == ext:
                    language = lang
                    break
                    
            if not language:
                logging.error(f"Unsupported file extension: {ext}")
                return False
                
            try:
                with open(input_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except UnicodeDecodeError:
                logging.error(f"Failed to read input file as UTF-8: {input_path}")
                return False
                
            processed_code = self._process_code(code, language, direction)
            if processed_code == "<Error>":
                return False

            output_dir = os.path.dirname(output_path)
            if output_dir: 
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as e:
                    logging.error(f"Failed to create output directory: {e}")
                    return False
                    
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(processed_code)
            except Exception as e:
                logging.error(f"Failed to write output file: {e}")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Error processing file: {e}")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Code Format Manager')
    parser.add_argument('input', help='Input file path')
    parser.add_argument('output', help='Output file path')
    parser.add_argument(
        'direction',
        choices=['format', 'unformat'],
        help='Processing direction: format or unformat'
    )
    parser.add_argument(
        '--config-dir',
        default='cfg',
        help='Configuration directory path (default: cfg)'
    )
    
    args = parser.parse_args()
    
    if not os.path.isabs(args.input):
        args.input = os.path.abspath(args.input)
        
    if not os.path.isabs(args.output):
        args.output = os.path.abspath(args.output)
        
    manager = CodeFormatManager(args.config_dir)
    direction = FormatDirection(args.direction)
    # manager.process_file(args.input, args.output, direction)
    if manager.process_file(args.input, args.output, direction):
        print(f"Processing complete. Output saved to: {args.output}")
    else:
        print("Processing failed. Check logs for details.")

if __name__ == "__main__":
    main()