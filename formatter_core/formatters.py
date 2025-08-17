from typing import Optional
import subprocess
import tempfile
import os
import logging
from .base import BaseFormatter
from io import StringIO
import ast
import tokenize
import yapf
import re
from .base import BaseFormatter

class UncrustifyFormatter(BaseFormatter):
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.FileHandler(os.path.join('logs/batch_processor.log'))
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            
    def _run_uncrustify(self, code: str, config_file: str, language: str, format_mode: bool = True) -> Optional[str]:
        try:
            suffix_map = {
                'cpp': '.cpp',
                'csharp': '.cs',
                'java': '.java'
            }
            suffix = suffix_map.get(language.lower(), '') 
            
            with tempfile.NamedTemporaryFile(mode='w+', suffix=suffix, delete=False) as temp_in:
                temp_in.write(code)
                temp_in_path = temp_in.name
                logging.debug(f"Temporarily enter the file path: {temp_in_path}")
                    
            temp_out_path = temp_in_path + '.out'
            logging.debug(f"Temporary output file path: {temp_out_path}")
                
            config_path = os.path.join(self.config_dir, config_file)
            logging.debug(f"The path of the configuration file used: {config_path}")
            if not os.path.exists(config_path):
                logging.error(f"Configuration file not found: {config_path}")
                return "<Error>"
                    
            cmd = ['uncrustify', '-c', config_path, '-f', temp_in_path, '-o', temp_out_path]
            if not format_mode:
                cmd.extend(['--no-backup'])
            logging.debug(f"Run commands: {' '.join(cmd)}")
                    
            result = subprocess.run(cmd, capture_output=True, text=True)
            logging.debug(f"Uncrustify Return code: {result.returncode}")
            logging.debug(f"Uncrustify Standard output: {result.stdout}")
            logging.debug(f"Uncrustify Error output: {result.stderr}")
                
            if result.returncode != 0:
                logging.error(f"Uncrustify error: {result.stderr}")
                return "<Error>"
                    
            with open(temp_out_path, 'r') as f:
                processed_code = f.read()
                logging.debug("The formatted code was successfully read")
                    
            os.unlink(temp_in_path)
            os.unlink(temp_out_path)
            logging.debug("Temporary file deleted")
                
            return processed_code
                
        except Exception as e:
            logging.error(f"Error in uncrustify processing: {e}")
            return "<Error>"
                
    def format_code(self, code: str, **kwargs) -> Optional[str]:
        language = kwargs.get('language')
        if not language:
            raise ValueError("Language must be specified")
                
        config_file = f"{language}_formatted.cfg"
        logging.debug(f"The configuration file used to format the code: {config_file}")
        return self._run_uncrustify(code, config_file, language, True)
            
    def unformat_code(self, code: str, **kwargs) -> Optional[str]:
        language = kwargs.get('language')
        if not language:
            raise ValueError("Language must be specified")
                
        config_file = f"{language}_unformatted.cfg"
        logging.debug(f"Unformat the code using the configuration file: {config_file}")
        return self._run_uncrustify(code, config_file, language, False)


class PythonFormatter(BaseFormatter):
    def __init__(self):
        # Define the control structure to be replaced and the corresponding replacement mode
        self.control_structure_patterns = {
            r'for\s+#\s*TODO:\s*Your\s+code\s+here:': 'for _tempmask_ in [None]:',
            r'if\s+#\s*TODO:\s*Your\s+code\s+here:': 'if [TEMPMASK]:',
            r'while\s+#\s*TODO:\s*Your\s+code\s+here:': 'while [TEMPMASK]:',
        }

        self.reverse_control_structure_patterns = {
            'for _tempmask_ in [None]:': 'for # TODO: Your code here:',
            'if [TEMPMASK]:': 'if # TODO: Your code here:',
            'while [TEMPMASK]:': 'while # TODO: Your code here:',
        }

        # Ensure that the log directory exists
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # Acquire logger
        self.logger = logging.getLogger('python_formatter')
        
        # Add a processor only when one is not available
        if not self.logger.handlers:
            # Create file processor
            log_file = os.path.join(log_dir, 'python_formatter.log')
            file_handler = logging.FileHandler(log_file)
            
            # Create formatter
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            
            # Add processor to logger
            self.logger.addHandler(file_handler)
            self.logger.setLevel(logging.INFO)

        # Configure the YAPF formatting style
        self.yapf_style = {
            'based_on_style': 'pep8',
            'spaces_before_comment': 2,
            'split_before_logical_operator': True,
            'column_limit': 100,
            'indent_width': 4,
        }

        # 初始化 SpaceReducer
        self.space_reducer = SpaceReducer("")

    def mask_control_structures(self, code: str) -> str:
        """Replace specific control structure comments with placeholders"""
        for pattern, replacement in self.control_structure_patterns.items():
            code = re.sub(pattern, replacement, code)
        return code

    def unmask_control_structures(self, code: str) -> str:
        """Replace the placeholder back to the original control structure comment"""
        for replacement, original in self.reverse_control_structure_patterns.items():
            code = code.replace(replacement, original)
        return code

    def format_code(self, code: str, **kwargs) -> Optional[str]:
        try:
            code = self.mask_control_structures(code)
            
            formatted_code, changed = yapf.yapf_api.FormatCode(
                code,
                style_config=self.yapf_style
            )
            formatted_code = self.unmask_control_structures(formatted_code)
            return formatted_code

        except Exception as e:
            self.logger.error(f"An error occurred during formatting: {e}")
            return None

    def unformat_code(self, code: str, **kwargs) -> Optional[str]:
        try:
            self.space_reducer.source = code
            self.space_reducer._tokenize_source()
            compressed_code = self.space_reducer.reduce_spaces()

            if compressed_code:
                compressed_code = self.unmask_control_structures(compressed_code)
                
                return compressed_code
            
            return None

        except Exception as e:
            self.logger.error(f"An error occurred during space compression: {e}")
            return None

class SpaceReducer:
    def __init__(self, source: str):
        self.source = source
        self.tokens = []
        if source:
            self._tokenize_source()

    def _tokenize_source(self):
        """Word segmentation of source code"""
        try:
            token_gen = tokenize.generate_tokens(StringIO(self.source).readline)
            self.tokens = list(token_gen)
        except tokenize.TokenError as e:
            logging.error(f"Word segmentation error: {e}")
            raise

    def _handle_empty_control_structure(self, token_idx):
        """Handle empty control structures"""
        if token_idx + 1 < len(self.tokens):
            next_token = self.tokens[token_idx + 1]
            if next_token.type in (tokenize.NEWLINE, tokenize.NL):
                return True
        return False

    def reduce_spaces(self) -> str:
        result = []
        prev_token = None
        line_start = True
        previous_was_newline = False
        
        for i, token in enumerate(self.tokens):
            tok_type = token.type
            tok_string = token.string
            start = token.start

            if line_start and tok_type not in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT):
                if prev_token and prev_token.end[0] != start[0]:
                    result.append(' ' * start[1])
                line_start = False

            if tok_type in (tokenize.NEWLINE, tokenize.NL):
                if not previous_was_newline:
                    result.append('\n')
                    previous_was_newline = True
                line_start = True
            elif tok_type == tokenize.COMMENT:
                if prev_token and prev_token.type not in (tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT):
                    result.append(' ')
                result.append(tok_string)
                previous_was_newline = False
            elif tok_type == tokenize.STRING:
                result.append(tok_string)
                previous_was_newline = False
            elif tok_type == tokenize.OP:
                result.append(tok_string)
                previous_was_newline = False
            elif tok_type in (tokenize.NAME, tokenize.NUMBER):
                if tok_type == tokenize.NAME and tok_string in ('if', 'while', 'for') and self._handle_empty_control_structure(i):
                    result.append(tok_string)
                else:
                    if prev_token and prev_token.type in (tokenize.NAME, tokenize.NUMBER):
                        result.append(' ')
                    result.append(tok_string)
                previous_was_newline = False
            elif tok_type in (tokenize.INDENT, tokenize.DEDENT):
                continue
            else:
                result.append(tok_string)
                previous_was_newline = False

            prev_token = token

        processed = ''.join(result)
        lines = processed.splitlines()
        
        cleaned_lines = []
        blank_line = False
        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                if not blank_line:
                    cleaned_lines.append('')
                    blank_line = True
            else:
                cleaned_lines.append(stripped)
                blank_line = False
                
        return '\n'.join(cleaned_lines) + '\n'