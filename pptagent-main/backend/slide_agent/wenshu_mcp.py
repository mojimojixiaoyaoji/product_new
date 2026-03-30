import requests
import json
from typing import Optional
from contextlib import contextmanager

__MCP_QUESTION_SERVER_URL = "http://10.40.0.98/mcp/server/ypDqUnyB0WbXdU3U/mcp"
__TOOL_QUESTION_NAME = "自然语言数据查询MCP"

# 默认认证令牌（需要替换）
__DEFAULT_QUESTION_AUTH = "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJqMkRZdEtOalpnM3d0TUYwbTJQN0N3V1NRdGJBaEswQm9ZZTQzem91UUN3In0.eyJleHAiOjE4MDQ3NjA2MTEsImlhdCI6MTc3MzMwODE2NSwiYXV0aF90aW1lIjoxNzczMjI0NjExLCJqdGkiOiJvbnJ0YWM6YTNiODc4ZGQtZDI3ZS1lOWZiLTRmNDItMDhmMDU4MjBhOGZhIiwiaXNzIjoiaHR0cHM6Ly9rZXljbG9hay5tZGlyaS5jb20vcmVhbG1zL2FsbGludGVjaGluY19jbG91ZCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiIwMWZiOTMyNS0xZjZiLTQ0NjctYTQzMS1hNDAzNjNhNDg4M2IiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJwcmR4aWFvbWlhbyIsInNpZCI6IjgzZGJjYmIwLThlMDUtOWQ0NS1lZTA4LTRkN2FkNmYzNmQwZiIsImFjciI6IjAiLCJhbGxvd2VkLW9yaWdpbnMiOlsiKiJdLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiZGVmYXVsdC1yb2xlcy1hbGxpbnRlY2hpbmNfY2xvdWQiLCJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwibmFtZSI6InhpYW9kb25nLndhbmcgeGlhb2Rvbmcud2FuZyIsInByZWZlcnJlZF91c2VybmFtZSI6InhpYW9kb25nLndhbmciLCJnaXZlbl9uYW1lIjoieGlhb2Rvbmcud2FuZyIsImZhbWlseV9uYW1lIjoieGlhb2Rvbmcud2FuZyIsImVtYWlsIjoieGlhb2Rvbmcud2FuZ0BhbGxpbnRlY2hpbmMuY29tIn0.TuXUvB2nXbFGklgElHIUxxTTHgcCsMOR1bzEUJW8js5fDJWfsKSwsl0F3IRlQdPhXnN7mEqq19QWN2eanIQmJhXnm1Y__StUoWyNfeE70Tg7bu1eFJQ4fD1aNzjPWYUULLVqAHCMO-E0T5_HmfSUOfk0OX2b5LpRGG1hvCso59t2V8hB56h4YMqlnB-J8t9cL-Jqp0OJi6OteocweP0LuLTTF5tGCRotXVIGx1e9CQtqxGo-YUE6LZyG_AAv7XqZa4l_WfiqoD3aAjVn9JMCwQvNVspZJKx2cGkXi7NokkroaLNfqW0m0JrwkNsNAkHCVOwHceb1u_sStAGNZBiDzg"


def __get_headers(auth: str) -> dict[str, str]:
    """生成请求头"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/Event-Stream",
        "User-Agent": "MCP Test Client",
        "Accept-Encoding": "identity",
        "Connection": "keep-alive",
        "MCP-Session-ID": "abcd"
    }


@contextmanager
def __create_session() -> requests.Session:
    """创建并自动清理 HTTP 会话"""
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()  # 关闭连接，释放资源


def mcp_tool_call(query: str, auth: str) -> str:
    """
    执行 MCP 工具调用 - 显传入认证令牌
    
    Args:
        query: 查询内容
        auth: 认证令牌
    
    Returns:
        工具调用响应的中的 data 字段（JSON 字符串），错误时返回空字符串
    """
    # 初始化载荷
    init_payload: dict = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2.0",
            "capabilities": {},
            "clientInfo": {"name": "MCP Test Client", "version": "1.0.0"}
        },
        "id": 1
    }
    
    # 工具调用载荷
    call_payload: dict = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": __TOOL_QUESTION_NAME,
            "arguments": {
                "query": query,
                "Authorization": auth
            }
        },
        "protocolVersion": "2.0",
        "capabilities": {},
        "clientInfo": {"name": "MCP Test Client", "version": "1.0.0"},
        "id": 2
    }
    
    headers: dict[str, str] = __get_headers(auth)
    
    try:
        with __create_session() as session:
            # 初始化
            resp1: requests.Response = session.post(
                __MCP_QUESTION_SERVER_URL,
                json=init_payload,
                headers=headers,
                timeout=30
            )
            resp1.raise_for_status()
            
            # 工具调用
            resp2: requests.Response = session.post(
                __MCP_QUESTION_SERVER_URL,
                json=call_payload,
                headers=headers,
                timeout=30
            )
            resp2.raise_for_status()
        
        # 防御性检查：HTTP 状态码
        if resp2.status_code != 200:
            print(f"HTTP 错误: 状态码 {resp2.status_code}, 响应内容: {resp2.text[:200]}")
            return ""
        
        # 防御性检查：响应为空
        if not resp2.text or not resp2.text.strip():
            print("错误: 响应内容为空")
            return ""
        
        # 解析响应
        try:
            data: dict = resp2.json()
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}, 响应内容: {resp2.text[:200]}")
            return ""
        
        # 防御性检查：响应包含 error 字段 (RPC 错误)
        if "error" in data:
            error_info = data.get("error", {})
            error_code = error_info.get("code", "unknown")
            error_msg = error_info.get("message", "Unknown error")
            print(f"RPC 错误: code={error_code}, message={error_msg}")
            return ""
        
        # 防御性检查：result 字段不存在
        if "result" not in data:
            print(f"错误: 响应中缺少 result 字段, 响应内容: {str(data)[:200]}")
            return ""
        
        # 提取 content 字段
        result_content = data.get("result", {}).get("content", [])
        if not result_content or not isinstance(result_content, list):
            print(f"错误: result.content 为空或格式错误, result: {str(data.get('result', {}))[:200]}")
            return ""
        
        # 提取 text 字段
        inner_text: str = result_content[0].get("text", "") if isinstance(result_content[0], dict) else ""
        if not inner_text:
            print("错误: inner_text 为空")
            return ""
        
        # 防御性检查：inner_text 解析
        try:
            inner_data: dict = json.loads(inner_text)
        except json.JSONDecodeError as e:
            print(f"inner_text JSON 解析失败: {e}, 内容: {inner_text[:200]}")
            return ""
        
        # 防御性检查：inner_data 中包含错误
        if not inner_data.get("success", True):
            error_msg = inner_data.get("error", "Unknown error")
            print(f"业务错误: {error_msg}")
            return ""
        
        # 返回 data 字段（JSON 字符串）
        return json.dumps(inner_data.get("data", {}), ensure_ascii=False)
    
    except requests.exceptions.Timeout:
        print("错误: 请求超时")
        return ""
    except requests.exceptions.ConnectionError as e:
        print(f"错误: 连接失败 - {e}")
        return ""
    except requests.exceptions.HTTPError as e:
        print(f"HTTP 错误: {e}")
        return ""
    except Exception as e:
        # 错误时返回空字符串
        print(f"exception: {e}")
        return ""


def mcp_tool_call_with_default_auth(query: str) -> str:
    """
    执行 MCP 工具调用 - 使用默认认证令牌
    
    Args:
        query: 查询内容
    
    Returns:
        工具调用响应中 data 字段（JSON 字符串），错误时返回空字符串
    """
    return mcp_tool_call(query, __DEFAULT_QUESTION_AUTH)

if __name__=="__main__":
# 导出别名（保持与原代码兼容）
    func1 = mcp_tool_call
    func2 = mcp_tool_call_with_default_questions

    data = mcp_tool_call_with_default_auth("查询华蓥近一周窑磨状态")
    print(data)
    print(json.loads(json.dumps(data, ensure_ascii=False)))
    # 用 unicode-escape 编码再解码
    s = str(data).encode('unicode-escape').decode('unicode-escape')
    print(s)
