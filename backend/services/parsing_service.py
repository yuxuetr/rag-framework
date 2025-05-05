import logging
from typing import Dict, List, Any, Optional, Tuple
import fitz  # PyMuPDF
import pandas as pd
from datetime import datetime
import os
import tempfile
import pytesseract  # OCR处理
from PIL import Image
import numpy as np
import markdown
import base64
import re
import io
from bs4 import BeautifulSoup
import tabula  # PDF表格提取
import camelot  # 另一个PDF表格提取工具
import pdfplumber
import cv2

logger = logging.getLogger(__name__)

class ParsingService:
    """
    PDF文档解析服务类
    
    该类提供多种解析策略来提取和构建PDF文档内容，包括：
    - 全文提取
    - 逐页解析
    - 基于标题的分段
    - 文本和表格混合解析
    - 图像文本提取
    - 表格结构化提取

    支持的文件格式：
    - PDF
    - Markdown
    - 文本文件
    """

    def __init__(self, ocr_lang: str = 'chi_sim+eng'):
        """
        初始化解析服务

        参数:
            ocr_lang (str): OCR识别的语言，默认为中文简体+英文
        """
        self.ocr_lang = ocr_lang
        self.temp_dir = tempfile.mkdtemp()
        self.image_counter = 0
        self.table_counter = 0

    def parse_document(self, file_path: str, content: str = None, method: str = 'comprehensive', 
                  file_type: str = 'pdf', metadata: dict = None, page_map: list = None,
                  extract_images: bool = True, extract_tables: bool = True) -> dict:
        """
        解析文档内容，支持PDF、Markdown等多种格式

        参数:
            file_path (str): 文档文件路径
            content (str, optional): 已提取的文档内容，如果为None，将从文件中读取
            method (str): 解析方法，可选值：
                - 'comprehensive': 全面解析（文本、表格、图像）
                - 'text_only': 仅提取文本
                - 'tables_only': 仅提取表格
                - 'images_only': 仅提取图像
                - 'by_pages': 按页解析
                - 'by_titles': 按标题分段解析
            file_type (str): 文件类型，可选值：'pdf', 'markdown', 'txt'
            metadata (dict): 文档元数据，如果为None将自动生成
            page_map (list): 页面映射数据
            extract_images (bool): 是否提取图像内容
            extract_tables (bool): 是否提取表格内容

        返回:
            dict: 解析后的文档数据，包括元数据和结构化内容
        """
        try:
            if metadata is None:
                metadata = {
                    "filename": os.path.basename(file_path),
                    "file_type": file_type,
                    "parsing_method": method,
                    "timestamp": datetime.now().isoformat()
                }
            
            parsed_content = []
            
            # 根据文件类型选择解析策略
            if file_type == 'pdf':
                if not content and not page_map:
                    content, page_map = self._extract_pdf_content(file_path)
                
                if method == 'comprehensive':
                    parsed_content = self._parse_pdf_comprehensive(
                        file_path, page_map, extract_images, extract_tables
                    )
                elif method == 'text_only':
                    parsed_content = self._parse_all_text(page_map)
                elif method == 'tables_only':
                    parsed_content = self._extract_tables_from_pdf(file_path)
                elif method == 'images_only':
                    parsed_content = self._extract_images_from_pdf(file_path)
                elif method == 'by_pages':
                    parsed_content = self._parse_by_pages(page_map)
                elif method == 'by_titles':
                    parsed_content = self._parse_by_titles(page_map)
                elif method == 'text_and_tables':
                    parsed_content = self._parse_text_and_tables(page_map)
                else:
                    raise ValueError(f"Unsupported parsing method for PDF: {method}")
                
                metadata["total_pages"] = len(page_map) if page_map else 0
                
            elif file_type == 'markdown':
                if not content:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                
                if method == 'comprehensive':
                    parsed_content = self._parse_markdown_comprehensive(content, file_path)
                elif method == 'text_only':
                    parsed_content = self._parse_markdown_text_only(content)
                elif method == 'tables_only':
                    parsed_content = self._extract_tables_from_markdown(content)
                else:
                    raise ValueError(f"Unsupported parsing method for Markdown: {method}")
                
                metadata["total_pages"] = 1  # Markdown视为单页
            
            elif file_type == 'txt':
                if not content:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                
                parsed_content = [{
                    "type": "text",
                    "content": content,
                    "page": 1
                }]
                
                metadata["total_pages"] = 1  # 文本文件视为单页
            
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # 创建文档级元数据
            document_data = {
                "metadata": metadata,
                "content": parsed_content
            }
            
            return document_data
            
        except Exception as e:
            logger.error(f"Error in parse_document: {str(e)}")
            raise
    
    def parse_pdf(self, text: str, method: str, metadata: dict, page_map: list = None) -> dict:
        """
        使用指定方法解析PDF文档 (兼容旧API)

        参数:
            text (str): PDF文档的文本内容
            method (str): 解析方法 ('all_text', 'by_pages', 'by_titles', 或 'text_and_tables')
            metadata (dict): 文档元数据，包括文件名和其他属性
            page_map (list): 包含每页内容和元数据的字典列表

        返回:
            dict: 解析后的文档数据，包括元数据和结构化内容

        异常:
            ValueError: 当page_map为空或指定了不支持的解析方法时抛出
        """
        try:
            if not page_map:
                raise ValueError("Page map is required for parsing.")
            
            parsed_content = []
            total_pages = len(page_map)
            
            if method == "all_text":
                parsed_content = self._parse_all_text(page_map)
            elif method == "by_pages":
                parsed_content = self._parse_by_pages(page_map)
            elif method == "by_titles":
                parsed_content = self._parse_by_titles(page_map)
            elif method == "text_and_tables":
                parsed_content = self._parse_text_and_tables(page_map)
            else:
                raise ValueError(f"Unsupported parsing method: {method}")
                
            # Create document-level metadata
            document_data = {
                "metadata": {
                    "filename": metadata.get("filename", ""),
                    "total_pages": total_pages,
                    "parsing_method": method,
                    "timestamp": datetime.now().isoformat()
                },
                "content": parsed_content
            }
            
            return document_data
            
        except Exception as e:
            logger.error(f"Error in parse_pdf: {str(e)}")
            raise

    def _parse_all_text(self, page_map: list) -> list:
        """
        将文档中的所有文本内容提取为连续流

        参数:
            page_map (list): 包含每页内容的字典列表

        返回:
            list: 包含带页码的文本内容的字典列表
        """
        return [{
            "type": "Text",
            "content": page["text"],
            "page": page["page"]
        } for page in page_map]

    def _parse_by_pages(self, page_map: list) -> list:
        """
        逐页解析文档，保持页面边界

        参数:
            page_map (list): 包含每页内容的字典列表

        返回:
            list: 包含带页码的分页内容的字典列表
        """
        parsed_content = []
        for page in page_map:
            parsed_content.append({
                "type": "Page",
                "page": page["page"],
                "content": page["text"]
            })
        return parsed_content

    def _parse_by_titles(self, page_map: list) -> list:
        """
        通过识别标题来解析文档并将内容组织成章节

        使用简单的启发式方法识别标题：
        长度小于60个字符且全部大写的行被视为章节标题

        参数:
            page_map (list): 包含每页内容的字典列表

        返回:
            list: 包含带标题和页码的分章节内容的字典列表
        """
        parsed_content = []
        current_title = None
        current_content = []

        for page in page_map:
            lines = page["text"].split('\n')
            for line in lines:
                # Simple heuristic: consider lines with less than 60 chars and all caps as titles
                if len(line.strip()) < 60 and line.isupper():
                    if current_title:
                        parsed_content.append({
                            "type": "section",
                            "title": current_title,
                            "content": '\n'.join(current_content),
                            "page": page["page"]
                        })
                    current_title = line.strip()
                    current_content = []
                else:
                    current_content.append(line)

        # Add the last section
        if current_title:
            parsed_content.append({
                "type": "section",
                "title": current_title,
                "content": '\n'.join(current_content),
                "page": page["page"]
            })

        return parsed_content

    def _parse_text_and_tables(self, page_map: list) -> list:
        """
        通过分离文本和表格内容来解析文档

        使用基本的表格检测启发式方法（存在'|'或制表符）
        来识别潜在的表格内容

        参数:
            page_map (list): 包含每页内容的字典列表

        返回:
            list: 包含分离的文本和表格内容（带页码）的字典列表
        """
        parsed_content = []
        for page in page_map:
            # Extract tables using tabula-py or similar library
            # For this example, we'll just simulate table detection
            content = page["text"]
            if '|' in content or '\t' in content:
                parsed_content.append({
                    "type": "table",
                    "content": content,
                    "page": page["page"]
                })
            else:
                parsed_content.append({
                    "type": "text",
                    "content": content,
                    "page": page["page"]
                })
        return parsed_content

    def _extract_pdf_content(self, file_path: str) -> Tuple[str, list]:
        """
        从PDF文件中提取内容

        参数:
            file_path (str): PDF文件路径

        返回:
            Tuple[str, list]: (完整文本内容, 页面映射列表)
        """
        full_text = ""
        page_map = []
        
        try:
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc, 1):
                    text = page.get_text("text")
                    full_text += text + "\n"
                    page_map.append({
                        "page": page_num,
                        "text": text.strip()
                    })
                    
            return full_text, page_map
        except Exception as e:
            logger.error(f"Error extracting PDF content: {str(e)}")
            raise
            
    def _parse_pdf_comprehensive(self, file_path: str, page_map: list, 
                                extract_images: bool = True, extract_tables: bool = True) -> list:
        """
        全面解析PDF，包括文本、表格和图像

        参数:
            file_path (str): PDF文件路径
            page_map (list): 页面映射
            extract_images (bool): 是否提取图像
            extract_tables (bool): 是否提取表格

        返回:
            list: 解析后的内容列表
        """
        parsed_content = []
        
        # 1. 提取文本内容
        for page in page_map:
            parsed_content.append({
                "type": "text",
                "content": page["text"],
                "page": page["page"],
                "metadata": {
                    "content_type": "text",
                    "page_number": page["page"]
                }
            })
        
        # 2. 提取表格内容
        if extract_tables:
            tables = self._extract_tables_from_pdf(file_path)
            parsed_content.extend(tables)
        
        # 3. 提取图像内容
        if extract_images:
            images = self._extract_images_from_pdf(file_path)
            parsed_content.extend(images)
        
        return parsed_content
        
    def _extract_tables_from_pdf(self, file_path: str) -> list:
        """
        从PDF中提取表格

        参数:
            file_path (str): PDF文件路径

        返回:
            list: 表格内容列表
        """
        tables_content = []
        
        try:
            # 使用多种库尝试提取表格，确保最佳结果
            
            # 1. 先尝试使用tabula-py
            try:
                logger.info("Extracting tables with tabula-py")
                tabula_tables = tabula.read_pdf(
                    file_path, 
                    pages='all',
                    multiple_tables=True
                )
                
                for i, table in enumerate(tabula_tables):
                    if not table.empty:
                        # 转换为Markdown格式
                        markdown_table = table.to_markdown()
                        tables_content.append({
                            "type": "table",
                            "content": markdown_table,
                            "page": self._get_table_page(file_path, i),
                            "metadata": {
                                "content_type": "table",
                                "table_id": f"tabula_{i+1}",
                                "rows": len(table),
                                "columns": len(table.columns),
                                "extraction_method": "tabula"
                            }
                        })
            except Exception as e:
                logger.warning(f"Tabula extraction failed: {str(e)}")
            
            # 2. 如果tabula提取不理想，尝试使用camelot
            if not tables_content:
                try:
                    logger.info("Extracting tables with camelot")
                    camelot_tables = camelot.read_pdf(
                        file_path,
                        pages='all',
                        flavor='lattice'  # 或者使用'stream'
                    )
                    
                    for i, table in enumerate(camelot_tables):
                        df = table.df
                        if not df.empty:
                            markdown_table = df.to_markdown()
                            tables_content.append({
                                "type": "table",
                                "content": markdown_table,
                                "page": table.page,
                                "metadata": {
                                    "content_type": "table",
                                    "table_id": f"camelot_{i+1}",
                                    "rows": table.shape[0],
                                    "columns": table.shape[1],
                                    "accuracy": table.accuracy,
                                    "extraction_method": "camelot"
                                }
                            })
                except Exception as e:
                    logger.warning(f"Camelot extraction failed: {str(e)}")
            
            # 3. 最后尝试使用pdfplumber
            if not tables_content:
                try:
                    logger.info("Extracting tables with pdfplumber")
                    with pdfplumber.open(file_path) as pdf:
                        for page_num, page in enumerate(pdf.pages, 1):
                            tables = page.extract_tables()
                            
                            for i, table_data in enumerate(tables):
                                if table_data:
                                    # 转换为DataFrame
                                    df = pd.DataFrame(table_data)
                                    markdown_table = df.to_markdown()
                                    
                                    tables_content.append({
                                        "type": "table",
                                        "content": markdown_table,
                                        "page": page_num,
                                        "metadata": {
                                            "content_type": "table",
                                            "table_id": f"pdfplumber_page{page_num}_table{i+1}",
                                            "rows": len(table_data),
                                            "columns": len(table_data[0]) if table_data else 0,
                                            "extraction_method": "pdfplumber"
                                        }
                                    })
                except Exception as e:
                    logger.warning(f"PDFPlumber extraction failed: {str(e)}")
            
            return tables_content
                
        except Exception as e:
            logger.error(f"Error extracting tables: {str(e)}")
            return []
    
    def _get_table_page(self, file_path: str, table_index: int) -> int:
        """
        尝试确定表格所在的页码
        
        参数:
            file_path (str): PDF文件路径
            table_index (int): 表格索引
            
        返回:
            int: 页码，如果无法确定则返回1
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    if len(tables) > table_index:
                        return page_num
                    table_index -= len(tables)
                
                # 如果找不到对应的表格，返回1
                return 1
        except:
            return 1
            
    def _extract_images_from_pdf(self, file_path: str) -> list:
        """
        从PDF中提取图像并进行OCR识别
        
        参数:
            file_path (str): PDF文件路径
            
        返回:
            list: 图像内容列表
        """
        images_content = []
        
        try:
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc, 1):
                    image_list = page.get_images(full=True)
                    
                    # 如果页面没有图像，尝试用另一种方法渲染页面
                    if not image_list:
                        # 将页面渲染为图像，然后进行OCR
                        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                        img_path = os.path.join(self.temp_dir, f"page_{page_num}.png")
                        pix.save(img_path)
                        
                        # 使用OpenCV检测页面中的图像区域
                        img = cv2.imread(img_path)
                        if img is not None:
                            # 转换为灰度
                            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            # 阈值处理
                            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
                            # 寻找轮廓
                            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            
                            # 筛选可能的图像区域
                            for i, contour in enumerate(contours):
                                # 获取边界矩形
                                x, y, w, h = cv2.boundingRect(contour)
                                
                                # 忽略太小的区域
                                if w < 100 or h < 100:
                                    continue
                                
                                # 提取潜在的图像区域
                                roi = img[y:y+h, x:x+w]
                                region_path = os.path.join(self.temp_dir, f"page_{page_num}_region_{i}.png")
                                cv2.imwrite(region_path, roi)
                                
                                # 执行OCR
                                image_text = self._perform_ocr(region_path)
                                
                                if image_text.strip():
                                    self.image_counter += 1
                                    images_content.append({
                                        "type": "image",
                                        "content": image_text,
                                        "page": page_num,
                                        "metadata": {
                                            "content_type": "image",
                                            "image_id": f"img_{self.image_counter}",
                                            "coordinates": {"x": x, "y": y, "width": w, "height": h},
                                            "extraction_method": "page_rendering"
                                        }
                                    })
                    
                    # 提取文档中嵌入的图像
                    for img_index, img_info in enumerate(image_list, 1):
                        xref = img_info[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # 保存为临时文件
                        img_filename = f"xref_{xref}.{base_image['ext']}"
                        img_path = os.path.join(self.temp_dir, img_filename)
                        
                        with open(img_path, "wb") as img_file:
                            img_file.write(image_bytes)
                        
                        # 执行OCR
                        image_text = self._perform_ocr(img_path)
                        
                        if image_text.strip():
                            self.image_counter += 1
                            images_content.append({
                                "type": "image",
                                "content": image_text,
                                "page": page_num,
                                "metadata": {
                                    "content_type": "image",
                                    "image_id": f"img_{self.image_counter}",
                                    "image_format": base_image['ext'],
                                    "image_size": len(image_bytes),
                                    "extraction_method": "embedded_image"
                                }
                            })
            
            return images_content
                
        except Exception as e:
            logger.error(f"Error extracting images: {str(e)}")
            return []
    
    def _perform_ocr(self, image_path: str) -> str:
        """
        对图像执行OCR识别
        
        参数:
            image_path (str): 图像文件路径
            
        返回:
            str: 识别出的文本
        """
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang=self.ocr_lang)
            return text
        except Exception as e:
            logger.error(f"OCR failed: {str(e)}")
            return ""

    def _parse_markdown_comprehensive(self, content: str, file_path: str = None) -> list:
        """
        全面解析Markdown内容，包括文本、表格和图像引用
        
        参数:
            content (str): Markdown内容
            file_path (str): Markdown文件路径，用于解析相对图像路径
            
        返回:
            list: 解析后的内容列表
        """
        parsed_content = []
        
        # 将Markdown转换为HTML以便结构化解析
        html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取所有段落文本
        texts = []
        for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            if p.text.strip():
                level = 0
                if p.name.startswith('h'):
                    level = int(p.name[1])
                
                texts.append({
                    "type": "text",
                    "content": p.text,
                    "page": 1,
                    "metadata": {
                        "content_type": "text",
                        "is_heading": p.name.startswith('h'),
                        "heading_level": level,
                        "tag": p.name
                    }
                })
        
        parsed_content.extend(texts)
        
        # 提取表格
        tables = []
        for table in soup.find_all('table'):
            # 将HTML表格转换为Markdown格式
            rows = []
            
            # 处理表头
            headers = []
            for th in table.find('thead').find_all('th') if table.find('thead') else []:
                headers.append(th.text.strip())
            
            if headers:
                rows.append('| ' + ' | '.join(headers) + ' |')
                rows.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
            
            # 处理表体
            for tr in table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr'):
                row_cells = []
                for td in tr.find_all(['td', 'th']):
                    row_cells.append(td.text.strip())
                rows.append('| ' + ' | '.join(row_cells) + ' |')
            
            markdown_table = '\n'.join(rows)
            self.table_counter += 1
            
            tables.append({
                "type": "table",
                "content": markdown_table,
                "page": 1,
                "metadata": {
                    "content_type": "table",
                    "table_id": f"md_table_{self.table_counter}",
                    "rows": len(rows) - (2 if headers else 0),
                    "columns": len(headers) if headers else (len(row_cells) if 'row_cells' in locals() else 0)
                }
            })
        
        parsed_content.extend(tables)
        
        # 提取图像引用并尝试OCR
        images = []
        for img in soup.find_all('img'):
            img_src = img.get('src', '')
            img_alt = img.get('alt', '')
            
            # 处理图像
            if img_src and file_path and not img_src.startswith(('http:', 'https:')):
                # 处理相对路径
                img_path = os.path.join(os.path.dirname(file_path), img_src)
                if os.path.exists(img_path):
                    # 执行OCR
                    image_text = self._perform_ocr(img_path)
                    if image_text.strip():
                        self.image_counter += 1
                        images.append({
                            "type": "image",
                            "content": image_text,
                            "page": 1,
                            "metadata": {
                                "content_type": "image",
                                "image_id": f"md_img_{self.image_counter}",
                                "image_src": img_src,
                                "image_alt": img_alt
                            }
                        })
        
        parsed_content.extend(images)
        
        # 提取代码块
        code_blocks = []
        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code and code.text.strip():
                code_blocks.append({
                    "type": "code",
                    "content": code.text,
                    "page": 1,
                    "metadata": {
                        "content_type": "code",
                        "language": code.get('class', [''])[0].replace('language-', '') if code.get('class') else ''
                    }
                })
        
        parsed_content.extend(code_blocks)
        
        return parsed_content
    
    def _parse_markdown_text_only(self, content: str) -> list:
        """
        仅提取Markdown中的文本内容
        
        参数:
            content (str): Markdown内容
            
        返回:
            list: 文本内容列表
        """
        # 移除Markdown格式符号
        # 去除标题符号
        text = re.sub(r'#{1,6}\s+', '', content)
        # 去除粗体和斜体
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        # 去除代码块
        text = re.sub(r'```[\s\S]*?```', '', text)
        # 去除行内代码
        text = re.sub(r'`(.+?)`', r'\1', text)
        # 去除链接
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
        # 去除图片
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        # 去除HTML标签
        text = re.sub(r'<.*?>', '', text)
        # 处理列表
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        return [{
            "type": "text",
            "content": text.strip(),
            "page": 1,
            "metadata": {
                "content_type": "text"
            }
        }]
    
    def _extract_tables_from_markdown(self, content: str) -> list:
        """
        从Markdown中提取表格
        
        参数:
            content (str): Markdown内容
            
        返回:
            list: 表格内容列表
        """
        tables = []
        
        # 表格正则表达式模式
        table_pattern = r'(\|.+\|\n)+?(\|\s*[-:]+[-|\s:]*\|\n)(\|.+\|\n)+'
        
        for match in re.finditer(table_pattern, content, re.MULTILINE):
            table_content = match.group(0)
            
            # 计算行数和列数
            lines = table_content.strip().split('\n')
            rows = len(lines) - 1  # 减去分隔行
            cols = len(lines[0].split('|')) - 2  # 减去两侧的空元素
            
            self.table_counter += 1
            tables.append({
                "type": "table",
                "content": table_content,
                "page": 1,
                "metadata": {
                    "content_type": "table",
                    "table_id": f"md_tbl_{self.table_counter}",
                    "rows": rows,
                    "columns": cols
                }
            })
        
        return tables 