import unittest
import os
import tempfile
import pandas as pd
import json
import shutil
from backend.services.loading_service import LoadingService

class TestLoadingService(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        self.loading_service = LoadingService()
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        self.txt_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.txt_file, "w", encoding="utf-8") as f:
            f.write("这是一个测试文本文件。\n它包含多行内容。\n用于测试TXT加载功能。")
        
        self.csv_file = os.path.join(self.temp_dir, "test.csv")
        data = {
            "姓名": ["张三", "李四", "王五"],
            "年龄": [25, 30, 35],
            "职业": ["工程师", "教师", "医生"]
        }
        pd.DataFrame(data).to_csv(self.csv_file, index=False)
        
        self.md_file = os.path.join(self.temp_dir, "test.md")
        with open(self.md_file, "w", encoding="utf-8") as f:
            f.write("# 测试标题\n\n## 子标题1\n\n这是一段Markdown文本，用于测试。\n\n## 子标题2\n\n- 列表项1\n- 列表项2\n- 列表项3")
    
    def tearDown(self):
        """清理测试环境"""
        # 删除测试文件
        for file_path in [self.txt_file, self.csv_file, self.md_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # 删除临时目录
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_load_txt(self):
        """测试TXT文件加载"""
        # 测试基本加载
        content = self.loading_service.load_txt(self.txt_file)
        self.assertIsNotNone(content)
        self.assertIn("这是一个测试文本文件", content)
        
        # 验证页面映射
        page_map = self.loading_service.get_page_map()
        self.assertEqual(len(page_map), 1)
        self.assertEqual(page_map[0]["page"], 1)
        
        # 测试总页数
        total_pages = self.loading_service.get_total_pages()
        self.assertEqual(total_pages, 1)
        
        # 测试带分块的加载
        content_chunked = self.loading_service.load_txt(
            self.txt_file,
            chunking_strategy="basic",
            chunking_options={"maxCharacters": 100}
        )
        self.assertIsNotNone(content_chunked)
    
    def test_load_csv(self):
        """测试CSV文件加载"""
        # 使用pandas加载
        content = self.loading_service.load_csv(self.csv_file)
        self.assertIsNotNone(content)
        self.assertIn("张三", content)
        self.assertIn("李四", content)
        
        # 使用csv模块加载
        content_csv = self.loading_service.load_csv(self.csv_file, use_pandas=False)
        self.assertIsNotNone(content_csv)
        self.assertIn("姓名", content_csv)
        self.assertIn("职业", content_csv)
        
        # 验证页面映射
        page_map = self.loading_service.get_page_map()
        self.assertEqual(len(page_map), 1)
        self.assertEqual(page_map[0]["page"], 1)
        
        # 验证元数据
        self.assertEqual(page_map[0]["metadata"]["file_type"], "csv")
    
    def test_load_markdown(self):
        """测试Markdown文件加载"""
        # 测试基本加载
        content = self.loading_service.load_markdown(self.md_file)
        self.assertIsNotNone(content)
        self.assertIn("测试标题", content)
        self.assertIn("子标题", content)
        
        # 测试带分块的加载
        content_chunked = self.loading_service.load_markdown(
            self.md_file,
            chunking_strategy="by_title",
            chunking_options={"combineTextUnderNChars": 100}
        )
        self.assertIsNotNone(content_chunked)
        
        # 验证页面映射
        page_map = self.loading_service.get_page_map()
        # 分块后应该有多个元素
        self.assertGreater(len(page_map), 0)
        
        # 所有块都应该有页码信息
        for block in page_map:
            self.assertIn("page", block)

    def test_save_document(self):
        """测试保存不同类型的文档"""
        # 创建临时的保存目录
        save_dir = os.path.join(self.temp_dir, "01-loaded-docs")
        os.makedirs(save_dir, exist_ok=True)
        
        # 分别测试不同类型文档的保存
        
        # 1. 测试保存TXT文档
        txt_content = self.loading_service.load_txt(self.txt_file)
        txt_chunks = self.loading_service.get_page_map()
        txt_metadata = {"total_pages": 1, "encoding": "utf-8"}
        
        txt_save_path = self.loading_service.save_document(
            filename=self.txt_file,
            chunks=txt_chunks,
            metadata=txt_metadata,
            loading_method="basic",
            chunking_strategy=None
        )
        
        self.assertTrue(os.path.exists(txt_save_path))
        
        # 验证保存的JSON文件内容
        with open(txt_save_path, 'r', encoding='utf-8') as f:
            txt_saved_data = json.load(f)
            self.assertEqual(txt_saved_data["document_type"], "txt")
            self.assertEqual(txt_saved_data["total_pages"], 1)
        
        # 2. 测试保存CSV文档
        csv_content = self.loading_service.load_csv(self.csv_file)
        csv_chunks = self.loading_service.get_page_map()
        csv_metadata = {"total_pages": 1, "delimiter": ",", "encoding": "utf-8"}
        
        csv_save_path = self.loading_service.save_document(
            filename=self.csv_file,
            chunks=csv_chunks,
            metadata=csv_metadata,
            loading_method="pandas"
        )
        
        self.assertTrue(os.path.exists(csv_save_path))
        
        # 验证保存的JSON文件内容
        with open(csv_save_path, 'r', encoding='utf-8') as f:
            csv_saved_data = json.load(f)
            self.assertEqual(csv_saved_data["document_type"], "csv")
            self.assertEqual(csv_saved_data["delimiter"], ",")
        
        # 3. 测试保存Markdown文档
        md_content = self.loading_service.load_markdown(
            self.md_file, 
            chunking_strategy="by_title"
        )
        md_chunks = self.loading_service.get_page_map()
        md_metadata = {"total_pages": 1}
        
        md_save_path = self.loading_service.save_document(
            filename=self.md_file,
            chunks=md_chunks,
            metadata=md_metadata,
            loading_method="basic",
            chunking_strategy="by_title"
        )
        
        self.assertTrue(os.path.exists(md_save_path))
        
        # 验证保存的JSON文件内容
        with open(md_save_path, 'r', encoding='utf-8') as f:
            md_saved_data = json.load(f)
            self.assertEqual(md_saved_data["document_type"], "md")
            self.assertEqual(md_saved_data["chunking_strategy"], "by_title")
            
        # 清理临时保存的文件
        if os.path.exists("01-loaded-docs"):
            shutil.rmtree("01-loaded-docs")

if __name__ == "__main__":
    unittest.main() 
