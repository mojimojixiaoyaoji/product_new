#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG 知识库客户端模块
用于调用知识库检索接口，获取增强内容
"""

import os
import logging
import requests
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)


class KnowledgeRagClient:
    """知识库 RAG 检索客户端"""
    
    def __init__(self):
        self.base_url = os.getenv("RAG_API_URL", "https://cic.mdiri.com/llm-knowledge-microservice/api/v1")
        self.endpoint = f"{self.base_url}/knowledge_retrieval_rag"
        self.token = os.getenv("RAG_API_TOKEN", "")
        self.timeout = int(os.getenv("RAG_TIMEOUT", "30"))
    
    def fetch_knowledge_rag(self, query_text: str) -> Optional[Dict[str, Any]]:
        """
        调用 RAG 知识库检索接口
        
        Args:
            query_text: 查询文本
            
        Returns:
            包含检索结果的字典，格式为:
            {
                "status": "success",
                "data": [
                    {
                        "file_name": str,
                        "file_url": str,
                        "chunk_text": str,
                        "score": float
                    },
                    ...
                ]
            }
            如果请求失败返回 None
        """
        logger.debug(f"RAG CLIENT: START, query_text: {query_text}")
        
        if not self.token:
            logger.debug("RAG CLIENT: END, RAG_API_TOKEN 未配置，跳过知识库检索")
            print("警告: RAG_API_TOKEN 未配置，跳过知识库检索")
            return None
        
        if not query_text or not query_text.strip():
            logger.debug("RAG CLIENT: END, 查询文本为空，跳过知识库检索")
            print("警告: 查询文本为空，跳过知识库检索")
            return None
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        
        payload = {
            "query": query_text
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    data = result.get("data", [])
                    logger.debug(f"RAG CLIENT: END, 检索成功，找到 {len(data)} 条相关知识")
                    logger.debug(f"RAG CLIENT: CONTENT, {result}")
                    print(f"RAG 检索成功，找到 {len(data)} 条相关知识")
                    return result
                else:
                    logger.debug(f"RAG CLIENT: END, 检索返回状态异常: {result.get('status')}")
                    print(f"RAG 检索返回状态异常: {result.get('status')}")
                    return None
            else:
                logger.debug(f"RAG CLIENT: END, 请求失败，状态码: {response.status_code}, 响应: {response.text}")
                print(f"RAG 请求失败，状态码: {response.status_code}, 响应: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.debug(f"RAG CLIENT: END, 请求超时 (超过 {self.timeout} 秒)")
            print(f"RAG 请求超时 (超过 {self.timeout} 秒)")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"RAG CLIENT: END, 请求异常: {e}")
            print(f"RAG 请求异常: {e}")
            return None
        except Exception as e:
            logger.debug(f"RAG CLIENT: END, 发生未知错误: {e}")
            print(f"RAG 调用发生未知错误: {e}")
            return None
    
    def format_rag_results(self, rag_response: Dict[str, Any], max_results: int = 5) -> str:
        """
        将 RAG 检索结果格式化为可读文本
        
        Args:
            rag_response: RAG 检索返回的结果
            max_results: 最多返回的结果数量
            
        Returns:
            格式化后的文本字符串
        """
        if not rag_response or rag_response.get("status") != "success":
            return ""
        
        data = rag_response.get("data", [])
        if not data:
            return ""
        
        # 按分数排序并限制数量
        sorted_data = sorted(data, key=lambda x: x.get("score", 0), reverse=True)[:max_results]
        
        formatted_parts = []
        for idx, item in enumerate(sorted_data, 1):
            file_name = item.get("file_name", "")
            chunk_text = item.get("chunk_text", "")
            score = item.get("score", 0)
            
            formatted_parts.append(
                f"[知识库参考 {idx}] 文件: {file_name} (相关度: {score:.2f})\n"
                f"内容摘要: {chunk_text}\n"
            )
        
        return "\n".join(formatted_parts)
    
    def get_enhanced_context(self, query_text: str, max_results: int = 5) -> str:
        """
        获取增强的上下文信息（便捷方法）
        
        Args:
            query_text: 查询文本
            max_results: 最多返回的结果数量
            
        Returns:
            格式化后的增强上下文文本，如果检索失败返回空字符串
        """
        rag_response = self.fetch_knowledge_rag(query_text)
        formatted_context = self.format_rag_results(rag_response, max_results)
        logger.debug(f"RAG CLIENT: FORMATTED_CONTEXT, {formatted_context}")
        return formatted_context


# 创建全局实例
_rag_client_instance = None


def get_rag_client() -> KnowledgeRagClient:
    """获取 RAG 客户端单例"""
    global _rag_client_instance
    if _rag_client_instance is None:
        _rag_client_instance = KnowledgeRagClient()
    return _rag_client_instance
