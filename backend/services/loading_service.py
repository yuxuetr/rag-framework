from pypdf import PdfReader
from unstructured.partition.pdf import partition_pdf
import pdfplumber
import fitz  # PyMuPDF
import logging
import os
from datetime import datetime
import json
import csv
import pandas as pd
from unstructured.partition.text import partition_text
from unstructured.partition.md import partition_md

logger = logging.getLogger(__name__)
"""
PDF文档加载服务类
    这个服务类提供了多种PDF文档加载方法，支持不同的加载策略和分块选项。
    主要功能：
    1. 支持多种PDF解析库：
        - PyMuPDF (fitz): 适合快速处理大量PDF文件，性能最佳
        - PyPDF: 适合简单的PDF文本提取，依赖较少
        - pdfplumber: 适合需要处理表格或需要文本位置信息的场景
        - unstructured: 适合需要更好的文档结构识别和灵活分块策略的场景
    
    2. 文档加载特性：
        - 保持页码信息
        - 支持文本分块
        - 提供元数据存储
        - 支持不同的加载策略（使用unstructured时）
    
    3. 支持多种文档格式：
        - PDF: 支持多种解析库和策略
        - TXT: 纯文本文件加载
        - CSV: 表格数据加载，支持格式化表格输出
        - Markdown: Markdown文档加载，支持结构化分块
 """
class LoadingService:
    """
    PDF文档加载服务类，提供多种PDF文档加载和处理方法。
    
    属性:
        total_pages (int): 当前加载PDF文档的总页数
        current_page_map (list): 存储当前文档的页面映射信息，每个元素包含页面文本和页码
    """
    
    def __init__(self):
        self.total_pages = 0
        self.current_page_map = []
    
    def load_pdf(self, file_path: str, method: str, strategy: str = None, chunking_strategy: str = None, chunking_options: dict = None) -> str:
        """
        加载PDF文档的主方法，支持多种加载策略。

        参数:
            file_path (str): PDF文件路径
            method (str): 加载方法，支持 'pymupdf', 'pypdf', 'pdfplumber', 'unstructured'
            strategy (str, optional): 使用unstructured方法时的策略，可选 'fast', 'hi_res', 'ocr_only'
            chunking_strategy (str, optional): 文本分块策略，可选 'basic', 'by_title'
            chunking_options (dict, optional): 分块选项配置

        返回:
            str: 提取的文本内容
        """
        try:
            if method == "pymupdf":
                return self._load_with_pymupdf(file_path)
            elif method == "pypdf":
                return self._load_with_pypdf(file_path)
            elif method == "pdfplumber":
                return self._load_with_pdfplumber(file_path)
            elif method == "unstructured":
                return self._load_with_unstructured(
                    file_path, 
                    strategy=strategy,
                    chunking_strategy=chunking_strategy,
                    chunking_options=chunking_options
                )
            else:
                raise ValueError(f"Unsupported loading method: {method}")
        except Exception as e:
            logger.error(f"Error loading PDF with {method}: {str(e)}")
            raise
    
    def get_total_pages(self) -> int:
        """
        获取当前加载文档的总页数。

        返回:
            int: 文档总页数
        """
        return max(page_data['page'] for page_data in self.current_page_map) if self.current_page_map else 0
    
    def get_page_map(self) -> list:
        """
        获取当前文档的页面映射信息。

        返回:
            list: 包含每页文本内容和页码的列表
        """
        return self.current_page_map
    
    def _load_with_pymupdf(self, file_path: str) -> str:
        """
        使用PyMuPDF库加载PDF文档。
        适合快速处理大量PDF文件，性能最佳。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        text_blocks = []
        try:
            with fitz.open(file_path) as doc:
                self.total_pages = len(doc)
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text("text")
                    if text.strip():
                        text_blocks.append({
                            "text": text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"PyMuPDF error: {str(e)}")
            raise
    
    def _load_with_pypdf(self, file_path: str) -> str:
        """
        使用PyPDF库加载PDF文档。
        适合简单的PDF文本提取，依赖较少。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        try:
            text_blocks = []
            with open(file_path, "rb") as file:
                pdf = PdfReader(file)
                self.total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_blocks.append({
                            "text": page_text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"PyPDF error: {str(e)}")
            raise
    
    def _load_with_unstructured(self, file_path: str, strategy: str = "fast", chunking_strategy: str = "basic", chunking_options: dict = None) -> str:
        """
        使用unstructured库加载PDF文档。
        适合需要更好的文档结构识别和灵活分块策略的场景。

        参数:
            file_path (str): PDF文件路径
            strategy (str): 加载策略，默认'fast'
            chunking_strategy (str): 分块策略，默认'basic'
            chunking_options (dict): 分块选项配置

        返回:
            str: 提取的文本内容
        """
        try:
            strategy_params = {
                "fast": {"strategy": "fast"},
                "hi_res": {"strategy": "hi_res"},
                "ocr_only": {"strategy": "ocr_only"}
            }            
         
            # Prepare chunking parameters based on strategy
            chunking_params = {}
            if chunking_strategy == "basic":
                chunking_params = {
                    "max_characters": chunking_options.get("maxCharacters", 4000),
                    "new_after_n_chars": chunking_options.get("newAfterNChars", 3000),
                    "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    "overlap": chunking_options.get("overlap", 200),
                    "overlap_all": chunking_options.get("overlapAll", False)
                }
            elif chunking_strategy == "by_title":
                chunking_params = {
                    "chunking_strategy": "by_title",
                    "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    "multipage_sections": chunking_options.get("multiPageSections", False)
                }
            
            # Combine strategy parameters with chunking parameters
            params = {**strategy_params.get(strategy, {"strategy": "fast"}), **chunking_params}
            
            elements = partition_pdf(file_path, **params)
            
            # Add debug logging
            for elem in elements:
                logger.debug(f"Element type: {type(elem)}")
                logger.debug(f"Element content: {str(elem)}")
                logger.debug(f"Element dir: {dir(elem)}")
            
            text_blocks = []
            pages = set()
            
            for elem in elements:
                metadata = elem.metadata.__dict__
                page_number = metadata.get('page_number')
                
                if page_number is not None:
                    pages.add(page_number)
                    
                    # Convert element to a serializable format
                    cleaned_metadata = {}
                    for key, value in metadata.items():
                        if key == '_known_field_names':
                            continue
                        
                        try:
                            # Try JSON serialization to test if value is serializable
                            json.dumps({key: value})
                            cleaned_metadata[key] = value
                        except (TypeError, OverflowError):
                            # If not serializable, convert to string
                            cleaned_metadata[key] = str(value)
                    
                    # Add additional element information
                    cleaned_metadata['element_type'] = elem.__class__.__name__
                    cleaned_metadata['id'] = str(getattr(elem, 'id', None))
                    cleaned_metadata['category'] = str(getattr(elem, 'category', None))
                    
                    text_blocks.append({
                        "text": str(elem),
                        "page": page_number,
                        "metadata": cleaned_metadata
                    })
            
            self.total_pages = max(pages) if pages else 0
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
            
        except Exception as e:
            logger.error(f"Unstructured error: {str(e)}")
            raise
    
    def _load_with_pdfplumber(self, file_path: str) -> str:
        """
        使用pdfplumber库加载PDF文档。
        适合需要处理表格或需要文本位置信息的场景。

        参数:
            file_path (str): PDF文件路径

        返回:
            str: 提取的文本内容
        """
        text_blocks = []
        try:
            with pdfplumber.open(file_path) as pdf:
                self.total_pages = len(pdf.pages)
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_blocks.append({
                            "text": page_text.strip(),
                            "page": page_num
                        })
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
        except Exception as e:
            logger.error(f"pdfplumber error: {str(e)}")
            raise
    
    def load_txt(self, file_path: str, encoding: str = 'utf-8', chunking_strategy: str = None, chunking_options: dict = None) -> str:
        """
        加载TXT文本文档。

        参数:
            file_path (str): TXT文件路径
            encoding (str): 文件编码，默认为utf-8
            chunking_strategy (str, optional): 文本分块策略，可选 'basic', 'by_title'
            chunking_options (dict, optional): 分块选项配置

        返回:
            str: 提取的文本内容
        """
        try:
            text_blocks = []
            
            # 使用unstructured库处理文本文件
            if chunking_strategy:
                # 准备分块参数
                chunking_params = {}
                if chunking_strategy == "basic":
                    chunking_params = {
                        "max_characters": chunking_options.get("maxCharacters", 4000),
                        "new_after_n_chars": chunking_options.get("newAfterNChars", 3000),
                        "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                        "overlap": chunking_options.get("overlap", 200),
                    }
                
                elements = partition_text(file_path, **chunking_params, encoding=encoding)
                
                for i, elem in enumerate(elements, 1):
                    metadata = elem.metadata.__dict__ if hasattr(elem, 'metadata') else {}
                    
                    cleaned_metadata = {}
                    for key, value in metadata.items():
                        if key == '_known_field_names':
                            continue
                        
                        try:
                            json.dumps({key: value})
                            cleaned_metadata[key] = value
                        except (TypeError, OverflowError):
                            cleaned_metadata[key] = str(value)
                    
                    # 添加元素信息
                    cleaned_metadata['element_type'] = elem.__class__.__name__
                    cleaned_metadata['id'] = str(getattr(elem, 'id', None))
                    cleaned_metadata['chunk_index'] = i
                    
                    text_blocks.append({
                        "text": str(elem),
                        "page": 1,  # 文本文件视为单页
                        "metadata": cleaned_metadata
                    })
            else:
                # 简单读取文本
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    text_blocks.append({
                        "text": content,
                        "page": 1
                    })
            
            self.total_pages = 1  # 文本文件视为单页
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
            
        except Exception as e:
            logger.error(f"Text loading error: {str(e)}")
            raise
    
    def load_csv(self, file_path: str, delimiter: str = ',', encoding: str = 'utf-8', use_pandas: bool = True) -> str:
        """
        加载CSV文档。

        参数:
            file_path (str): CSV文件路径
            delimiter (str): 字段分隔符，默认为逗号
            encoding (str): 文件编码，默认为utf-8
            use_pandas (bool): 是否使用pandas加载，默认为True

        返回:
            str: 提取的文本内容，格式化为表格文本
        """
        try:
            text_content = ""
            
            if use_pandas:
                # 使用pandas读取CSV文件
                df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding)
                text_content = df.to_string(index=False)
            else:
                # 使用csv模块读取
                rows = []
                with open(file_path, 'r', encoding=encoding) as file:
                    csv_reader = csv.reader(file, delimiter=delimiter)
                    header = next(csv_reader)
                    rows.append(header)
                    for row in csv_reader:
                        rows.append(row)
                
                # 格式化为文本表格
                col_widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
                formatted_rows = []
                
                # 添加表头
                header_row = [str(rows[0][i]).ljust(col_widths[i]) for i in range(len(rows[0]))]
                formatted_rows.append(" | ".join(header_row))
                
                # 添加分隔线
                separator = ["-" * col_widths[i] for i in range(len(rows[0]))]
                formatted_rows.append(" | ".join(separator))
                
                # 添加数据行
                for row in rows[1:]:
                    formatted_row = [str(row[i]).ljust(col_widths[i]) for i in range(len(row))]
                    formatted_rows.append(" | ".join(formatted_row))
                
                text_content = "\n".join(formatted_rows)
            
            # 创建文本块
            text_blocks = [{
                "text": text_content,
                "page": 1,  # CSV文件视为单页
                "metadata": {
                    "file_type": "csv",
                    "delimiter": delimiter,
                    "encoding": encoding
                }
            }]
            
            self.total_pages = 1
            self.current_page_map = text_blocks
            return text_content
            
        except Exception as e:
            logger.error(f"CSV loading error: {str(e)}")
            raise
    
    def load_markdown(self, file_path: str, encoding: str = 'utf-8', chunking_strategy: str = None, chunking_options: dict = None) -> str:
        """
        加载Markdown文档。

        参数:
            file_path (str): Markdown文件路径
            encoding (str): 文件编码，默认为utf-8
            chunking_strategy (str, optional): 文本分块策略，可选 'basic', 'by_title'
            chunking_options (dict, optional): 分块选项配置

        返回:
            str: 提取的文本内容
        """
        try:
            text_blocks = []
            
            # 使用unstructured库处理Markdown文件
            if chunking_strategy:
                # 准备分块参数
                chunking_params = {}
                if chunking_strategy == "basic":
                    chunking_params = {
                        "max_characters": chunking_options.get("maxCharacters", 4000),
                        "new_after_n_chars": chunking_options.get("newAfterNChars", 3000),
                        "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                        "overlap": chunking_options.get("overlap", 200),
                    }
                elif chunking_strategy == "by_title":
                    chunking_params = {
                        "chunking_strategy": "by_title",
                        "combine_text_under_n_chars": chunking_options.get("combineTextUnderNChars", 2000),
                    }
                
                elements = partition_md(file_path, **chunking_params)
                
                for i, elem in enumerate(elements, 1):
                    metadata = elem.metadata.__dict__ if hasattr(elem, 'metadata') else {}
                    
                    cleaned_metadata = {}
                    for key, value in metadata.items():
                        if key == '_known_field_names':
                            continue
                        
                        try:
                            json.dumps({key: value})
                            cleaned_metadata[key] = value
                        except (TypeError, OverflowError):
                            cleaned_metadata[key] = str(value)
                    
                    # 添加元素信息
                    cleaned_metadata['element_type'] = elem.__class__.__name__
                    cleaned_metadata['id'] = str(getattr(elem, 'id', None))
                    cleaned_metadata['category'] = str(getattr(elem, 'category', None))
                    cleaned_metadata['chunk_index'] = i
                    
                    text_blocks.append({
                        "text": str(elem),
                        "page": 1,  # Markdown文件视为单页
                        "metadata": cleaned_metadata
                    })
            else:
                # 简单读取文本
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    text_blocks.append({
                        "text": content,
                        "page": 1,
                        "metadata": {
                            "file_type": "markdown"
                        }
                    })
            
            self.total_pages = 1  # Markdown文件视为单页
            self.current_page_map = text_blocks
            return "\n".join(block["text"] for block in text_blocks)
            
        except Exception as e:
            logger.error(f"Markdown loading error: {str(e)}")
            raise
    
    def save_document(self, filename: str, chunks: list, metadata: dict, loading_method: str, strategy: str = None, chunking_strategy: str = None) -> str:
        """
        保存处理后的文档数据。

        参数:
            filename (str): 原文件名
            chunks (list): 文档分块列表
            metadata (dict): 文档元数据
            loading_method (str): 使用的加载方法
            strategy (str, optional): 使用的加载策略
            chunking_strategy (str, optional): 使用的分块策略

        返回:
            str: 保存的文件路径
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            file_extension = os.path.splitext(filename)[1].lower()
            base_name = os.path.basename(filename).replace(file_extension, '').split('_')[0]
            
            # 确定文档类型
            doc_type = ''
            if file_extension == '.pdf':
                doc_type = 'pdf'
            elif file_extension == '.txt':
                doc_type = 'txt'
            elif file_extension == '.csv':
                doc_type = 'csv'
            elif file_extension in ['.md', '.markdown']:
                doc_type = 'md'
            else:
                doc_type = 'doc'  # 默认文档类型
            
            # 根据不同文档类型和加载方法构建文档名称
            if doc_type == 'pdf' and loading_method == "unstructured" and strategy:
                doc_name = f"{base_name}_{loading_method}_{strategy}_{chunking_strategy}_{timestamp}"
            elif chunking_strategy:
                doc_name = f"{base_name}_{doc_type}_{loading_method}_{chunking_strategy}_{timestamp}"
            else:
                doc_name = f"{base_name}_{doc_type}_{loading_method}_{timestamp}"
            
            # 构建文档数据结构，确保所有值都是可序列化的
            document_data = {
                "filename": str(filename),
                "document_type": str(doc_type),
                "total_chunks": int(len(chunks)),
                "total_pages": int(metadata.get("total_pages", 1)),
                "loading_method": str(loading_method),
                "loading_strategy": str(strategy) if loading_method == "unstructured" and strategy else None,
                "chunking_strategy": str(chunking_strategy) if chunking_strategy else None,
                "chunking_method": "loaded",
                "timestamp": datetime.now().isoformat(),
                "chunks": chunks
            }
            
            # 添加特定文档类型的元数据
            if doc_type == 'csv' and metadata.get('delimiter'):
                document_data['delimiter'] = metadata.get('delimiter')
            if metadata.get('encoding'):
                document_data['encoding'] = metadata.get('encoding')
            
            # 保存到文件
            filepath = os.path.join("01-loaded-docs", f"{doc_name}.json")
            os.makedirs("01-loaded-docs", exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(document_data, f, ensure_ascii=False, indent=2)
                
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            raise
