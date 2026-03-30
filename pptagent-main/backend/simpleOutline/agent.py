import os
import random

from google.adk.agents import Agent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools import BaseTool
from typing import Dict, List, Any, AsyncGenerator, Optional, Union
from create_model import create_model
from tools import DocumentSearch
from dotenv import load_dotenv
import prompt
from rag_client import get_rag_client
load_dotenv()

def before_model_callback(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    # 1. 检查用户输入
    agent_name = callback_context.agent_name
    history_length = len(llm_request.contents)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型前的callback, 现在Agent共有{history_length}条历史记录,metadata数据为：{metadata}")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None
def after_model_callback(callback_context: CallbackContext, llm_response: LlmResponse) -> Optional[LlmResponse]:
    # 1. 检查用户输入，注意如果是llm的stream模式，那么response_data的结果是一个token的结果，还有可能是工具的调用
    agent_name = callback_context.agent_name
    response_parts = llm_response.content.parts
    part_texts =[]
    for one_part in response_parts:
        part_text = one_part.text
        if part_text is not None:
            part_texts.append(part_text)
    part_text_content = "\n".join(part_texts)
    metadata = callback_context.state.get("metadata")
    print(f"调用了{agent_name}模型后的callback, 这次模型回复{response_parts}条信息,metadata数据为：{metadata},回复内容是: {part_text_content}")
    #清空contents,不需要上一步的拆分topic的记录, 不能在这里清理，否则，每次调用工具都会清除记忆，白操作了
    # llm_request.contents.clear()
    # 返回 None，继续调用 LLM
    return None

def after_tool_callback(
    tool: BaseTool, args: Dict[str, Any], tool_context: ToolContext, tool_response: Dict
) -> Optional[Dict]:

  tool_name = tool.name
  print(f"调用了{tool_name}工具后的callback, tool_response数据为：{tool_response}")
  return None


class OutlineAgent(LlmAgent):
    def __init__(self, **kwargs):
        # 根据环境变量决定是否启用 DocumentSearch 工具
        enable_document_search = os.getenv("ENABLE_DOCUMENT_SEARCH", "true").lower() in ("true", "1", "yes", "on")
        tools = [DocumentSearch] if enable_document_search else []
        
        if enable_document_search:
            print("DocumentSearch 工具已启用")
        else:
            print("DocumentSearch 工具已禁用")
        
        super().__init__(
            name="outline_agent",
            model=create_model(model=os.environ["LLM_MODEL"], provider=os.environ["MODEL_PROVIDER"]),
            description="根据要求生成PPT大纲",
            instruction=self._get_dynamic_instruction,
            before_model_callback=before_model_callback,
            after_model_callback=after_model_callback,
            after_tool_callback=after_tool_callback,
            tools=tools,
            **kwargs
        )

    def _get_user_content_from_context(self, callback_context: CallbackContext) -> str | None:
        """
        获取用户的输入
        """
        # 1) 通过回调上下文的 user_content（如果该属性存在）
        user_content = getattr(callback_context, "user_content", None)
        if user_content and getattr(user_content, "parts", None):
            for part in user_content.parts:
                text = getattr(part, "text", None)
                if text:
                    return text
        return None

    def _get_dynamic_instruction(self, ctx: InvocationContext) -> str:
        """动态整合所有研究发现并生成指令"""
        # 从metadata中获取language
        metadata = ctx.state.get("metadata", {})
        language = metadata.get("language", "chinese")  # 默认中文
        COMPANY_INTRO = prompt.COMPANY_INTRO
        
        # 获取用户输入
        user_input = self._get_user_content_from_context(ctx)
        
        # 调用 RAG 知识库获取增强内容
        rag_enhanced_context = ""
        if user_input:
            try:
                rag_client = get_rag_client()
                rag_enhanced_context = rag_client.get_enhanced_context(user_input, max_results=5)
                if rag_enhanced_context:
                    rag_enhanced_context = f"以下是从知识库检索到的相关参考资料，可用于丰富大纲内容：\n\n{rag_enhanced_context}"
                else:
                    rag_enhanced_context = ""
            except Exception as e:
                print(f"RAG 知识库调用失败: {e}")
                rag_enhanced_context = ""
        
        # 根据不同的的输入长度，形成不同的prompt
        if len(user_input) > prompt.USER_INPUT_NUMBER:
            prompt_instruction = prompt.OUTLINE_INSTRUCTION_NO_SEARCH.format(
                language=language,
                COMPANY_INTRO=COMPANY_INTRO,
                RAG_ENHANCED_CONTEXT=rag_enhanced_context
            )
        else:
            prompt_instruction = prompt.OUTLINE_INSTRUCTION_WITH_SEARCH.format(
                language=language,
                COMPANY_INTRO=COMPANY_INTRO,
                RAG_ENHANCED_CONTEXT=rag_enhanced_context
            )
        return prompt_instruction

root_agent = OutlineAgent()
