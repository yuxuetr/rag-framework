// src/pages/LoadFile.jsx
import React, { useState, useEffect } from 'react';
import RandomImage from '../components/RandomImage';
import { apiBaseUrl } from '../config/config';

interface ChunkMetadata {
  chunk_id: string;
  page_number: number;
  word_count: number;
  page_range: string;
  [key: string]: any;
}

interface Chunk {
  content: string;
  text?: string;
  metadata: ChunkMetadata;
}

interface DocumentMetadata {
  total_pages?: number;
  total_chunks?: number;
  loading_method?: string;
  chunking_method?: string;
  timestamp?: string;
  [key: string]: any;
}

interface LoadedContent {
  chunks: Chunk[];
  total_pages: number;
  total_chunks: number;
  loading_method: string;
  chunking_method: string;
  timestamp: string;
  document_type?: string;
  [key: string]: any;
}

interface Document {
  name: string;
  metadata?: DocumentMetadata;
}

const LoadFile = () => {
  const [file, setFile] = useState<File | null>(null);
  const [fileType, setFileType] = useState<string>('pdf');
  const [loadingMethod, setLoadingMethod] = useState('pymupdf');
  const [encoding, setEncoding] = useState('utf-8');
  const [delimiter, setDelimiter] = useState(',');
  const [usePandas, setUsePandas] = useState(true);
  const [unstructuredStrategy, setUnstructuredStrategy] = useState('fast');
  const [chunkingStrategy, setChunkingStrategy] = useState('basic');
  const [chunkingOptions, setChunkingOptions] = useState({
    maxCharacters: 4000,
    newAfterNChars: 3000,
    combineTextUnderNChars: 500,
    overlap: 200,
    overlapAll: false,
    multiPageSections: false
  });
  const [loadedContent, setLoadedContent] = useState<LoadedContent | null>(null);
  const [status, setStatus] = useState('');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' 或 'documents'
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);

  useEffect(() => {
    fetchDocuments();
  }, []);

  // 根据文件类型自动设置推荐的加载方法
  useEffect(() => {
    console.log("文件类型变更:", fileType);
    if (fileType === 'pdf') {
      setLoadingMethod('pymupdf');
    } else if (fileType === 'txt' || fileType === 'md') {
      setLoadingMethod('basic');
    } else if (fileType === 'csv') {
      setLoadingMethod('pandas');
    }
  }, [fileType]);

  // 添加调试日志
  useEffect(() => {
    console.log("当前状态 - 文件:", file ? file.name : "无文件", "加载方法:", loadingMethod);
  }, [file, loadingMethod]);

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents?type=loaded`);
      const data = await response.json();
      setDocuments(data.documents);
    } catch (error) {
      console.error('Error fetching documents:', error);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const selectedFile = files[0];
    setFile(selectedFile);
    
    // 根据文件扩展名设置文件类型
    const fileName = selectedFile.name.toLowerCase();
    if (fileName.endsWith('.pdf')) {
      setFileType('pdf');
      setLoadingMethod('pymupdf');  // 直接设置加载方法
    } else if (fileName.endsWith('.txt')) {
      setFileType('txt');
      setLoadingMethod('basic');  // 直接设置加载方法
    } else if (fileName.endsWith('.csv')) {
      setFileType('csv');
      setLoadingMethod('pandas');  // 直接设置加载方法
    } else if (fileName.endsWith('.md') || fileName.endsWith('.markdown')) {
      setFileType('md');
      setLoadingMethod('basic');  // 直接设置加载方法
    } else {
      setFileType('other');
      setLoadingMethod('');  // 未知文件类型，清空加载方法
    }
  };

  const handleProcess = async () => {
    if (!file || !loadingMethod) {
      setStatus('请选择所有必需的选项');
      return;
    }

    setStatus('加载中...');
    setLoadedContent(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_type', fileType);
      formData.append('loading_method', loadingMethod);
      
      // 根据文件类型添加不同的参数
      if (fileType === 'pdf' && loadingMethod === 'unstructured') {
        formData.append('strategy', unstructuredStrategy);
        formData.append('chunking_strategy', chunkingStrategy);
        formData.append('chunking_options', JSON.stringify(chunkingOptions));
      } else if (fileType === 'txt' || fileType === 'md') {
        formData.append('encoding', encoding);
        if (chunkingStrategy) {
          formData.append('chunking_strategy', chunkingStrategy);
          formData.append('chunking_options', JSON.stringify(chunkingOptions));
        }
      } else if (fileType === 'csv') {
        formData.append('delimiter', delimiter);
        formData.append('encoding', encoding);
        formData.append('use_pandas', String(usePandas));
      }

      const response = await fetch(`${apiBaseUrl}/load`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setLoadedContent(data.loaded_content);
      setStatus('文件加载成功!');
      fetchDocuments();
      setActiveTab('preview');

    } catch (error) {
      console.error('Error:', error);
      setStatus(`错误: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const handleDeleteDocument = async (docName: string) => {
    try {
      const response = await fetch(`${apiBaseUrl}/documents/${docName}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setStatus('文档删除成功');
      fetchDocuments();
      if (selectedDoc?.name === docName) {
        setSelectedDoc(null);
        setLoadedContent(null);
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      setStatus(`删除文档错误: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const handleViewDocument = async (doc: Document) => {
    try {
      setStatus('加载文档...');
      const response = await fetch(`${apiBaseUrl}/documents/${doc.name}.json`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setSelectedDoc(doc);
      setLoadedContent(data);
      setActiveTab('preview');
      setStatus('');
    } catch (error) {
      console.error('Error loading document:', error);
      setStatus(`加载文档错误: ${error instanceof Error ? error.message : '未知错误'}`);
    }
  };

  const renderRightPanel = () => {
    return (
      <div className="p-4">
        {/* 标签页切换 */}
        <div className="flex mb-4 border-b">
          <button
            className={`px-4 py-2 ${
              activeTab === 'preview'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('preview')}
          >
            文档预览
          </button>
          <button
            className={`px-4 py-2 ml-4 ${
              activeTab === 'documents'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-600'
            }`}
            onClick={() => setActiveTab('documents')}
          >
            文档管理
          </button>
        </div>

        {/* 内容区域 */}
        {activeTab === 'preview' ? (
          loadedContent ? (
            <div>
              <h3 className="text-xl font-semibold mb-4">文档内容</h3>
              <div className="mb-4 p-3 border rounded bg-gray-100">
                <h4 className="font-medium mb-2">文档信息</h4>
                <div className="text-sm text-gray-600">
                  <p>文档类型: {loadedContent.document_type || 'N/A'}</p>
                  <p>页数: {loadedContent.total_pages || 'N/A'}</p>
                  <p>分块数: {loadedContent.total_chunks || 'N/A'}</p>
                  <p>加载方法: {loadedContent.loading_method || 'N/A'}</p>
                  <p>分块方法: {loadedContent.chunking_method || 'N/A'}</p>
                  <p>处理日期: {loadedContent.timestamp ? 
                    new Date(loadedContent.timestamp).toLocaleString() : 'N/A'}</p>
                </div>
              </div>
              <div className="space-y-3 max-h-[calc(100vh-300px)] overflow-y-auto">
                {loadedContent.chunks?.map((chunk, index) => (
                  <div key={chunk.metadata?.chunk_id || index} className="p-3 border rounded bg-gray-50">
                    <div className="font-medium text-sm text-gray-500 mb-1">
                      分块 {chunk.metadata?.chunk_id || index + 1} 
                      {chunk.metadata?.page_number && `(页 ${chunk.metadata.page_number})`}
                    </div>
                    <div className="text-xs text-gray-400 mb-2">
                      {chunk.metadata?.word_count && `词数: ${chunk.metadata.word_count}`} 
                      {chunk.metadata?.page_range && `| 页码范围: ${chunk.metadata.page_range}`}
                    </div>
                    <div className="text-sm mt-2">
                      <div className="text-gray-600">{chunk.content || chunk.text}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <RandomImage message="上传并加载文件或选择现有文档以在此处查看结果" />
          )
        ) : (
          // 文档管理页面
          <div>
            <h3 className="text-xl font-semibold mb-4">文档管理</h3>
            <div className="space-y-4">
              {documents.map((doc) => (
                <div key={doc.name} className="p-4 border rounded-lg bg-gray-50">
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-lg">{doc.name}</h4>
                      <div className="text-sm text-gray-600 mt-1">
                        <p>文档类型: {doc.metadata?.document_type || '未知'}</p>
                        <p>页数: {doc.metadata?.total_pages || 'N/A'}</p>
                        <p>分块数: {doc.metadata?.total_chunks || 'N/A'}</p>
                        <p>加载方法: {doc.metadata?.loading_method || 'N/A'}</p>
                        <p>分块方法: {doc.metadata?.chunking_method || 'N/A'}</p>
                        <p>创建时间: {doc.metadata?.timestamp ? 
                          new Date(doc.metadata.timestamp).toLocaleString() : 'N/A'}</p>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleViewDocument(doc)}
                        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                      >
                        查看
                      </button>
                      <button
                        onClick={() => handleDeleteDocument(doc.name)}
                        className="px-3 py-1 bg-red-500 text-white rounded hover:bg-red-600"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              {documents.length === 0 && (
                <div className="text-center text-gray-500 py-8">
                  没有可用的文档
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-6">加载文件</h2>
      
      <div className="grid grid-cols-12 gap-6">
        {/* Left Panel */}
        <div className="col-span-3 space-y-4">
          <div className="p-4 border rounded-lg bg-white shadow-sm">
            <div>
              <label className="block text-sm font-medium mb-1">上传文件</label>
              <input
                type="file"
                accept=".pdf,.txt,.csv,.md,.markdown"
                onChange={handleFileChange}
                className="block w-full border rounded px-3 py-2"
              />
              {file && (
                <div className="mt-2 text-sm text-gray-600">
                  选择的文件类型: {fileType.toUpperCase()}
                </div>
              )}
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium mb-1">加载方法</label>
              <select
                value={loadingMethod}
                onChange={(e) => setLoadingMethod(e.target.value)}
                className="block w-full p-2 border rounded"
              >
                {fileType === 'pdf' && (
                  <>
                    <option value="pymupdf">PyMuPDF</option>
                    <option value="pypdf">PyPDF</option>
                    <option value="pdfplumber">PDFPlumber</option>
                    <option value="unstructured">Unstructured</option>
                  </>
                )}
                {fileType === 'txt' && (
                  <>
                    <option value="basic">基本文本加载</option>
                    <option value="unstructured">Unstructured</option>
                  </>
                )}
                {fileType === 'csv' && (
                  <>
                    <option value="pandas">Pandas</option>
                    <option value="csv">CSV模块</option>
                  </>
                )}
                {fileType === 'md' && (
                  <>
                    <option value="basic">基本文本加载</option>
                    <option value="unstructured">Unstructured</option>
                  </>
                )}
                {!file && <option value="">请先选择文件</option>}
              </select>
            </div>

            {/* 文件特定选项 */}
            {(fileType === 'txt' || fileType === 'md') && (
              <div className="mt-4">
                <label className="block text-sm font-medium mb-1">编码</label>
                <select
                  value={encoding}
                  onChange={(e) => setEncoding(e.target.value)}
                  className="block w-full p-2 border rounded"
                >
                  <option value="utf-8">UTF-8</option>
                  <option value="utf-16">UTF-16</option>
                  <option value="gbk">GBK</option>
                  <option value="gb2312">GB2312</option>
                  <option value="iso-8859-1">ISO-8859-1</option>
                </select>
              </div>
            )}

            {fileType === 'csv' && (
              <>
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-1">分隔符</label>
                  <select
                    value={delimiter}
                    onChange={(e) => setDelimiter(e.target.value)}
                    className="block w-full p-2 border rounded"
                  >
                    <option value=",">逗号 (,)</option>
                    <option value=";">分号 (;)</option>
                    <option value="\t">制表符 (Tab)</option>
                    <option value="|">竖线 (|)</option>
                  </select>
                </div>
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-1">编码</label>
                  <select
                    value={encoding}
                    onChange={(e) => setEncoding(e.target.value)}
                    className="block w-full p-2 border rounded"
                  >
                    <option value="utf-8">UTF-8</option>
                    <option value="gbk">GBK</option>
                    <option value="gb2312">GB2312</option>
                    <option value="iso-8859-1">ISO-8859-1</option>
                  </select>
                </div>
              </>
            )}

            {/* Unstructured特定选项 */}
            {loadingMethod === 'unstructured' && (
              <>
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-1">Unstructured策略</label>
                  <select
                    value={unstructuredStrategy}
                    onChange={(e) => setUnstructuredStrategy(e.target.value)}
                    className="block w-full p-2 border rounded"
                  >
                    <option value="fast">快速</option>
                    <option value="hi_res">高分辨率</option>
                    <option value="ocr_only">仅OCR</option>
                  </select>
                </div>

                <div className="mt-4">
                  <label className="block text-sm font-medium mb-1">分块策略</label>
                  <select
                    value={chunkingStrategy}
                    onChange={(e) => setChunkingStrategy(e.target.value)}
                    className="block w-full p-2 border rounded"
                  >
                    <option value="basic">基础分块</option>
                    <option value="by_title">按标题分块</option>
                  </select>
                </div>

                {chunkingStrategy === 'basic' && (
                  <div className="mt-4 space-y-3">
                    <div>
                      <label className="block text-sm font-medium mb-1">最大字符数</label>
                      <input
                        type="number"
                        value={chunkingOptions.maxCharacters}
                        onChange={(e) => setChunkingOptions(prev => ({
                          ...prev,
                          maxCharacters: parseInt(e.target.value)
                        }))}
                        className="block w-full p-2 border rounded"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">字符数阈值</label>
                      <input
                        type="number"
                        value={chunkingOptions.newAfterNChars}
                        onChange={(e) => setChunkingOptions(prev => ({
                          ...prev,
                          newAfterNChars: parseInt(e.target.value)
                        }))}
                        className="block w-full p-2 border rounded"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">合并小于N字符的文本</label>
                      <input
                        type="number"
                        value={chunkingOptions.combineTextUnderNChars}
                        onChange={(e) => setChunkingOptions(prev => ({
                          ...prev,
                          combineTextUnderNChars: parseInt(e.target.value)
                        }))}
                        className="block w-full p-2 border rounded"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">重叠字符数</label>
                      <input
                        type="number"
                        value={chunkingOptions.overlap}
                        onChange={(e) => setChunkingOptions(prev => ({
                          ...prev,
                          overlap: parseInt(e.target.value)
                        }))}
                        className="block w-full p-2 border rounded"
                      />
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        checked={chunkingOptions.overlapAll}
                        onChange={(e) => setChunkingOptions(prev => ({
                          ...prev,
                          overlapAll: e.target.checked
                        }))}
                        className="mr-2"
                      />
                      <label className="text-sm font-medium">全部重叠</label>
                    </div>
                  </div>
                )}

                {chunkingStrategy === 'by_title' && (
                  <div className="mt-4 space-y-3">
                    <div>
                      <label className="block text-sm font-medium mb-1">合并小于N字符的文本</label>
                      <input
                        type="number"
                        value={chunkingOptions.combineTextUnderNChars}
                        onChange={(e) => setChunkingOptions(prev => ({
                          ...prev,
                          combineTextUnderNChars: parseInt(e.target.value)
                        }))}
                        className="block w-full p-2 border rounded"
                      />
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        checked={chunkingOptions.multiPageSections}
                        onChange={(e) => setChunkingOptions(prev => ({
                          ...prev,
                          multiPageSections: e.target.checked
                        }))}
                        className="mr-2"
                      />
                      <label className="text-sm font-medium">多页节</label>
                    </div>
                  </div>
                )}
              </>
            )}

            <button 
              onClick={handleProcess}
              className="mt-4 w-full px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
              disabled={!file || !loadingMethod}
            >
              加载文件
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

        {/* Right Panel */}
        <div className="col-span-9 border rounded-lg bg-white shadow-sm">
          {renderRightPanel()}
        </div>
      </div>
    </div>
  );
};

export default LoadFile;