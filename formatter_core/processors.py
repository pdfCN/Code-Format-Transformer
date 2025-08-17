
from typing import Optional, List, Dict, Pattern, Tuple
import re
from tree_sitter_languages import get_parser
from .base import BaseCodeProcessor

class BaseTreeSitterProcessor(BaseCodeProcessor):
    def __init__(self):
        self.parsers = {
            'cpp': get_parser('cpp'),
            'java': get_parser('java'),
            'csharp': get_parser('c_sharp'),
        }
        self.placeholder_template = "__PROTECTED_{}_PLACEHOLDER__"

    def _protect_node_range(self, byte_code: bytes, start: int, end: int) -> Tuple[int, str]:
        content = byte_code[start:end].decode('utf-8')
        return end, content

class WhitespaceProcessor(BaseTreeSitterProcessor):
    def __init__(self):
        super().__init__()
        self.protected_nodes = {
            'cpp': {
                'comment', 'line_comment', 'block_comment', 
                'preproc_include', 'preproc_def', 'preproc_function_def',
                'preproc_directive', 'preproc_if', 'preproc_ifdef',
                'preproc_else', 'preproc_elif', 'preproc_endif',
                'preproc_call', 'system_lib_string'
            },
            'java': {
                'line_comment', 'block_comment', 'annotation'
            },
            'python': {
                'comment', 'string', 'decorator'
            },
            'csharp': {
                'comment', 'string_literal', 'attribute_section',
                'preprocessor_directive', 'using_directive', 'attribute_list',
                'verbatim_string_literal', 'raw_string_literal',
                'interpolated_string_expression', 'preproc_if',
                'preproc_else', 'preproc_elif', 'preproc_endif',
                'preproc_region', 'preproc_endregion', 'preproc_define',
                'preproc_undef', 'preproc_load'
            }
        }

    def _protect_segments(self, code: str, lang: str) -> tuple[str, dict]:
        protected_segments = {}
        byte_code = code.encode('utf-8')
        parser = self.parsers.get(lang)
        if not parser:
            raise ValueError(f"Unsupported language: {lang}")

        tree = parser.parse(byte_code)
        cursor = tree.walk()

        protected_ranges = []
        def visit_node():
            if cursor.node.type in self.protected_nodes.get(lang, set()):
                start = cursor.node.start_byte
                end = cursor.node.end_byte
                new_end, content = self._protect_node_range(byte_code, start, end)
                if cursor.node.type in {'comment', 'line_comment', 'block_comment'}:
                    content = content + '\n'
                protected_ranges.append((start, new_end, content))

            if cursor.goto_first_child():
                visit_node()
                while cursor.goto_next_sibling():
                    visit_node()
                cursor.goto_parent()

        visit_node()

        modified_code = code
        for i, (start, end, content) in enumerate(protected_ranges):
            placeholder = self.placeholder_template.format(i)
            protected_segments[placeholder] = content
            modified_code = modified_code.replace(content, placeholder)

        return modified_code, protected_segments

    def _restore_segments(self, code: str, segments: dict) -> str:
        for placeholder, content in segments.items():
            code = code.replace(placeholder, content)
        return code

    def _restore_comments(self, code: str, comments: Dict[str, str]) -> str:
        for placeholder, comment in comments.items():
            code = code.replace(placeholder, comment + '\n')
        return code

    def process(self, code: str, **kwargs) -> str:
        if 'lang' not in kwargs:
            raise ValueError("Language must be specified")
        lang = kwargs['lang']
        
        protected_code, segments = self._protect_segments(code, lang)

        compressed = re.sub(r'\s*;\s*', ';', protected_code)
        compressed = re.sub(r'{\s+', '{', compressed)
        compressed = re.sub(r'\s+}', '}', compressed)
        compressed = re.sub(r'\n+', '', compressed)
        compressed = re.sub(r'\s+', ' ', compressed)

        result = self._restore_segments(compressed, segments)
        return result.strip()

class CommentProcessor(BaseTreeSitterProcessor):
    def __init__(self):
        super().__init__()
        self.comment_types = {
            'cpp': {
                'line_comment': 'single_line',
                'comment': 'multi_line',
                'block_comment': 'multi_line'
            },
            'java': {
                'line_comment': 'single_line',
                'block_comment': 'multi_line',
                'javadoc': 'javadoc',
                'end_of_line_comment': 'single_line',  # 行末注释
                'doc_comment': 'documentation'      
            },
            'csharp': {
                'line_comment': 'single_line',
                'block_comment': 'multi_line',
                'documentation_comment': 'javadoc'
            }
        }

    def _protect_comments(self, code: str, lang: str) -> tuple[str, Dict[str, str]]:
        protected_comments = {}
        byte_code = code.encode('utf-8')
        parser = self.parsers.get(lang)
        if not parser:
            raise ValueError(f"Unsupported language: {lang}")

        tree = parser.parse(byte_code)
        cursor = tree.walk()

        comments = []
        def visit_node():
            node_type = cursor.node.type
            if node_type in self.comment_types.get(lang, {}):
                start = cursor.node.start_byte
                end = cursor.node.end_byte
                new_end, content = self._protect_node_range(byte_code, start, end)
                if not content.startswith(' '):
                    content = ' ' + content
                comments.append((start, new_end, content))

            if cursor.goto_first_child():
                visit_node()
                while cursor.goto_next_sibling():
                    visit_node()
                cursor.goto_parent()

        visit_node()

        modified_code = code
        for i, (start, end, content) in enumerate(comments):
            placeholder = self.placeholder_template.format(i)
            protected_comments[placeholder] = content
            modified_code = modified_code.replace(byte_code[start:end].decode('utf-8'), placeholder)

        return modified_code, protected_comments

    def _restore_comments(self, code: str, comments: Dict[str, str]) -> str:
        for placeholder, comment in comments.items():
            code = code.replace(placeholder, comment)
        return code

    def process(self, code: str, **kwargs) -> str:
        if 'lang' not in kwargs:
            raise ValueError("Language must be specified")
        lang = kwargs['lang']
        mode = kwargs.get('mode', 'preserve')
        
        if mode == 'preserve':
            modified_code, comments = self._protect_comments(code, lang)
            return self._restore_comments(modified_code, comments)
        elif mode == 'remove':
            tree = self.parsers[lang].parse(code.encode('utf-8'))
            comment_ranges = []
            cursor = tree.walk()

            def collect_comments():
                if cursor.node.type in self.comment_types.get(lang, {}):
                    start = cursor.node.start_byte
                    end = cursor.node.end_byte
                    new_end, _ = self._find_node_end_newline(
                        code.encode('utf-8'), 
                        end
                    )
                    comment_ranges.append((start, new_end))
                if cursor.goto_first_child():
                    collect_comments()
                    while cursor.goto_next_sibling():
                        collect_comments()
                    cursor.goto_parent()

            collect_comments()
            
            result = code
            for start, end in reversed(comment_ranges):
                result = result[:start] + result[end:]
            return result
        
        return code
