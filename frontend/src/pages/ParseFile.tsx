import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

interface ParsedContent {
  metadata: {
    total_pages?: number;
    parsing_method?: string;
    timestamp?: string;
    file_type?: string;
    [key: string]: any;
  };
  content: Array<{
    type: string;
    content: string;
    page: number;
    title?: string;
    metadata?: {
      content_type?: string;
      [key: string]: any;
    };
  }>;
}

const ParseFile = () => {
  const [file, setFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState<string>('pdf');
  const [loadingMethod, setLoadingMethod] = useState('pymupdf');
  const [parsingOption, setParsingOption] = useState('comprehensive');
  const [extractImages, setExtractImages] = useState(true);
  const [extractTables, setExtractTables] = useState(true);
  const [parsedContent, setParsedContent] = useState<ParsedContent | null>(null);
  const [status, setStatus] = useState('');
  const [docName, setDocName] = useState('');
  const [isProcessed, setIsProcessed] = useState(false);

  // 当文件类型变化时自动调整解析选项
  useEffect(() => {
    if (fileType === 'pdf') {
      setLoadingMethod('pymupdf');
    } else if (fileType === 'markdown' || fileType === 'md') {
      setLoadingMethod('basic');
    } else if (fileType === 'txt') {
      setLoadingMethod('basic');
    }
  }, [fileType]);

  const handleProcess = async () => {
    if (!file || !loadingMethod || !parsingOption) {
      setStatus('请选择所有必需的选项');
      return;
    }

    setStatus('处理中...');
    setParsedContent(null);
    setIsProcessed(false);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('loading_method', loadingMethod);
      formData.append('parsing_option', parsingOption);
      formData.append('file_type', fileType);
      formData.append('extract_images', String(extractImages));
      formData.append('extract_tables', String(extractTables));

      const response = await fetch(`${apiBaseUrl}/parse`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setParsedContent(data.parsed_content);
      setStatus('处理成功完成!');
      setIsProcessed(true);
    } catch (error) {
      console.error('Error:', error);
      setStatus(`错误: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const selectedFile = files[0];
    setFile(selectedFile);
    
    // 根据文件扩展名设置文件类型
    const fileName = selectedFile.name.toLowerCase();
    if (fileName.endsWith('.pdf')) {
      setFileType('pdf');
    } else if (fileName.endsWith('.md') || fileName.endsWith('.markdown')) {
      setFileType('markdown');
    } else if (fileName.endsWith('.txt')) {
      setFileType('txt');
    } else {
      setFileType('pdf'); // 默认为PDF
    }
    
    // 设置文档名
    const baseName = fileName.split('.')[0];
    setDocName(baseName);
  };

  const renderParsingOptions = () => {
    if (fileType === 'pdf') {
      return (
        <select
          value={parsingOption}
          onChange={(e) => setParsingOption(e.target.value)}
          className="block w-full p-2 border rounded"
        >
          <option value="comprehensive">全面解析 (文本+表格+图像)</option>
          <option value="text_only">仅文本</option>
          <option value="tables_only">仅表格</option>
          <option value="images_only">仅图像</option>
          <option value="by_pages">按页面</option>
          <option value="by_titles">按标题</option>
          <option value="text_and_tables">文本和表格</option>
        </select>
      );
    } else if (fileType === 'markdown') {
      return (
        <select
          value={parsingOption}
          onChange={(e) => setParsingOption(e.target.value)}
          className="block w-full p-2 border rounded"
        >
          <option value="comprehensive">全面解析 (文本+表格+图像)</option>
          <option value="text_only">仅文本</option>
          <option value="tables_only">仅表格</option>
        </select>
      );
    } else {
      return (
        <select
          value={parsingOption}
          onChange={(e) => setParsingOption(e.target.value)}
          className="block w-full p-2 border rounded"
        >
          <option value="text_only">文本解析</option>
        </select>
      );
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">解析文件</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel (3/12) */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            <div>
              <label className="block text-sm font-medium mb-1">上传文件</label>
              <input
                type="file"
                accept=".pdf,.md,.markdown,.txt"
                onChange={handleFileSelect}
                className="block w-full border rounded px-3 py-2"
                required
              />
              {file && (
                <div className="mt-2 text-sm text-gray-600">
                  文件类型: {fileType.toUpperCase()}
                </div>
              )}
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1">加载工具</label>
              <select
                value={loadingMethod}
                onChange={(e) => setLoadingMethod(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                {fileType === 'pdf' && (
                  <>
                    <option value="pymupdf">PyMuPDF</option>
                    <option value="pypdf">PyPDF</option>
                    <option value="unstructured">Unstructured</option>
                    <option value="pdfplumber">PDF Plumber</option>
                  </>
                )}
                {fileType === 'markdown' && (
                  <>
                    <option value="basic">基本解析</option>
                  </>
                )}
                {fileType === 'txt' && (
                  <>
                    <option value="basic">基本解析</option>
                  </>
                )}
              </select>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1">解析选项</label>
              {renderParsingOptions()}
            </div>

            {(fileType === 'pdf' || fileType === 'markdown') && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={extractImages}
                    onChange={(e) => setExtractImages(e.target.checked)}
                    className="mr-2"
                    id="extract-images"
                  />
                  <label htmlFor="extract-images" className="text-sm">提取图像内容 (OCR)</label>
                </div>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={extractTables}
                    onChange={(e) => setExtractTables(e.target.checked)}
                    className="mr-2"
                    id="extract-tables"
                  />
                  <label htmlFor="extract-tables" className="text-sm">提取表格内容</label>
                </div>
              </div>
            )}

            <button 
              onClick={handleProcess}
              className="mt-4 w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              disabled={!file}
            >
              解析文件
            </button>
          </div>

          {status && (
            <div className={`p-4 rounded-lg ${
              status.includes('错误') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
            }`}>
              {status}
            </div>
          )}
        </div>

        {/* Right Panel (9/12) */}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {parsedContent ? (
            <div className="p-4">
              <h3 className="text-xl font-semibold mb-4">解析结果</h3>
              <div className="mb-4 p-3 border rounded bg-gray-100">
                <h4 className="font-medium mb-2">文档信息</h4>
                <div className="text-sm text-gray-600">
                  <p>文件类型: {parsedContent.metadata?.file_type || fileType}</p>
                  <p>总页数: {parsedContent.metadata?.total_pages}</p>
                  <p>解析方法: {parsedContent.metadata?.parsing_method}</p>
                  <p>时间戳: {parsedContent.metadata?.timestamp && new Date(parsedContent.metadata.timestamp).toLocaleString()}</p>
                </div>
              </div>
              <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                {parsedContent.content.map((item, idx) => (
                  <div key={idx} className="p-3 border rounded bg-gray-50">
                    <div className="font-medium text-sm text-gray-500 mb-1">
                      {item.type === 'image' ? '图像' : item.type === 'table' ? '表格' : '文本'} - 
                      {item.page && `页 ${item.page}`}
                      {item.metadata?.content_type && ` - ${item.metadata.content_type}`}
                    </div>
                    {item.title && (
                      <div className="font-bold text-gray-700 mb-2">
                        {item.title}
                      </div>
                    )}
                    <div className={`text-sm ${item.type === 'table' ? 'font-mono whitespace-pre' : 'text-gray-600'}`}>
                      {item.content}
                    </div>
                    {item.metadata && item.type === 'image' && (
                      <div className="mt-2 text-xs text-gray-400">
                        图像ID: {item.metadata.image_id}, 
                        提取方法: {item.metadata.extraction_method}
                      </div>
                    )}
                    {item.metadata && item.type === 'table' && (
                      <div className="mt-2 text-xs text-gray-400">
                        表格ID: {item.metadata.table_id}, 
                        行数: {item.metadata.rows}, 
                        列数: {item.metadata.columns}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <RandomImage message="上传并解析文件以在此处查看结果" />
          )}
        </div>
      </div>
    </div>
  );
};

export default ParseFile; 