#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @File  : wenshu_api.py
# @Desc  : 包装 wenshu_mcp.py 为 FastAPI 服务，兼容 ChartDataAPI 接口

import os
import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from wenshu_mcp import mcp_tool_call_with_default_auth

app = FastAPI(title="WenShu Data API", description="包装 wenshu_mcp.py 的 MCP 工具调用为 REST API")


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str
    type: Optional[str] = "chart"


class QueryResponse(BaseModel):
    """查询响应模型"""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@app.post("/query", response_model=QueryResponse)
async def query_data(request: QueryRequest):
    """
    数据查询接口 - 兼容 ChartDataAPI 格式
    
    请求格式:
    {
        "query": "查询内容",
        "type": "chart"  # 兼容现有接口
    }
    
    响应格式:
    {
        "success": true/false,
        "data": {...},
        "error": "错误信息"
    }
    """
    try:
        print(f"收到查询请求: query={request.query}, type={request.type}")
        
        # 防御性检查：query 不能为空
        if not request.query or not request.query.strip():
            return QueryResponse(
                success=False,
                error="查询内容不能为空"
            )
        
        # 调用 MCP 工具获取数据
        result = mcp_tool_call_with_default_auth(request.query)

        # 打印返回的 result json
        print(f"查询结果: {result}")

        # 防御性检查：结果为空
        if not result:
            return QueryResponse(
                success=False,
                error="查询返回空结果，请稍后重试或检查服务状态"
            )
        
        # 防御性检查：结果解析
        try:
            data = json.loads(result)
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}, 原始结果: {result[:200]}")
            return QueryResponse(
                success=False,
                error=f"数据解析失败: {str(e)}"
            )
        
        return QueryResponse(
            success=True,
            data=data
        )
        
    except Exception as e:
        print(f"查询失败: {e}")
        return QueryResponse(
            success=False,
            error=f"服务内部错误: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("WENSHU_API_PORT", "8001"))
    print(f"启动 WenShu API 服务，端口: {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
