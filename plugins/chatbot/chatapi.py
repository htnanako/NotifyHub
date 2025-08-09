import httpx
import re
import logging
import time
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from tenacity import retry, wait_random_exponential, stop_after_attempt

from notifyhub.plugins.chatbot.utils import UserRecords, config
from notifyhub.plugins.chatbot.constants import (
    LOG_PREFIX,
    DEFAULT_TIMEOUT,
    O1_MODEL_PREFIX,
    SYSTEM_ROLE,
    USER_ROLE,
    ASSISTANT_ROLE,
    ERROR_CODE,
)


logger = logging.getLogger(__name__)



@dataclass
class ChatResponse:
    """聊天响应数据类"""
    success: bool
    content: str
    error_code: Optional[int] = None
    error_message: Optional[str] = None


def get_error_message(status_code: int) -> str:
    """获取错误信息"""
    return ERROR_CODE.get(status_code, f'[ERROR: {status_code}] 未知错误，请检查日志 | Unknown error, please check the log')


def convert_markdown_links_to_html(text: str) -> str:
    """将Markdown链接转换为HTML链接"""
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    
    def replace_link(match):
        title = match.group(1)
        url = match.group(2)
        return f'<a href="{url}">{title}</a>'
    
    return re.sub(pattern, replace_link, text)


def build_request_headers() -> Dict[str, str]:
    """构建请求头"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}"
    }


def build_messages_payload(query: str, username: str) -> List[Dict[str, str]]:
    """构建消息载荷"""
    messages = []
    
    # 确定系统角色类型
    system_role = USER_ROLE if config.model.startswith(O1_MODEL_PREFIX) else SYSTEM_ROLE
    
    # 添加自定义提示词
    if config.custom_prompt:
        current_date = time.strftime("%Y-%m-%d", time.localtime())
        messages.append({
            "role": system_role,
            "content": config.custom_prompt.format(date=current_date)
        })
    
    # 添加上下文记录
    if config.context_num:
        user_records = UserRecords()
        context_records = user_records.get_records(username=username)
        messages.extend(context_records)
    
    # 添加用户查询
    messages.append({
        "role": USER_ROLE,
        "content": query
    })
    
    return messages


def build_request_payload(query: str, username: str) -> Dict[str, Any]:
    """构建完整的请求载荷"""

    logger.info(f"{LOG_PREFIX} Chat ask: {query}")

    payload = {
        "model": config.model,
        "messages": build_messages_payload(query, username)
    }
    
    return payload


def save_conversation_context(username: str, query: str, answer: str) -> None:
    """保存对话上下文"""
    if not config.context_num:
        return
    
    user_records = UserRecords()
    
    # 保存用户消息
    user_content = {
        "role": USER_ROLE,
        "content": query
    }
    user_records.add_record(username=username, record=user_content)
    
    # 保存助手回复
    assistant_content = {
        "role": ASSISTANT_ROLE,
        "content": answer
    }
    user_records.add_record(username=username, record=assistant_content)


def parse_chat_response(response_data: Dict[str, Any]) -> Optional[str]:
    """解析聊天响应"""
    try:
        choices = response_data.get('choices', [])
        if not choices:
            logger.error(f"{LOG_PREFIX} 响应中没有choices字段")
            return None
        
        message = choices[0].get('message', {})
        if not message:
            logger.error(f"{LOG_PREFIX} 响应中没有message字段")
            return None
        
        content = message.get('content', '')
        if not content:
            logger.error(f"{LOG_PREFIX} 响应中没有content字段")
            return None
        
        return content
    except (KeyError, IndexError) as e:
        logger.error(f"{LOG_PREFIX} 解析响应数据失败: {e}")
        return None


async def make_chat_request(payload: Dict[str, Any], headers: Dict[str, str]) -> ChatResponse:
    """发送聊天请求"""
    try:
        async with httpx.AsyncClient(
            proxy=config.proxy if config.proxy else None,
            timeout=DEFAULT_TIMEOUT
        ) as client:
            response = await client.post(
                url=f"{config.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            
            if response.status_code == 200:
                response_data = response.json()
                content = parse_chat_response(response_data)
                
                if content is None:
                    return ChatResponse(
                        success=False,
                        content="解析响应数据失败",
                        error_message="响应数据格式错误"
                    )
                
                # 转换Markdown链接为HTML
                processed_content = convert_markdown_links_to_html(content)
                logger.info(f'{LOG_PREFIX} Chat answer: {processed_content}')
                
                return ChatResponse(
                    success=True,
                    content=processed_content
                )
            else:
                error_message = get_error_message(response.status_code)
                logger.error(f"{LOG_PREFIX} HTTP错误: {response.status_code} - {error_message}")
                
                return ChatResponse(
                    success=False,
                    content=error_message,
                    error_code=response.status_code,
                    error_message=error_message
                )
                
    except httpx.TimeoutException:
        error_message = "请求超时，请稍后重试"
        logger.error(f"{LOG_PREFIX} 请求超时")
        return ChatResponse(
            success=False,
            content=error_message,
            error_message=error_message
        )
    except httpx.RequestError as e:
        error_message = f"网络请求失败: {str(e)}"
        logger.error(f"{LOG_PREFIX} 网络请求错误: {e}")
        return ChatResponse(
            success=False,
            content=error_message,
            error_message=error_message
        )
    except json.JSONDecodeError as e:
        error_message = "响应数据格式错误"
        logger.error(f"{LOG_PREFIX} JSON解析错误: {e}")
        return ChatResponse(
            success=False,
            content=error_message,
            error_message=error_message
        )
    except Exception as e:
        error_message = f"思考失败: {str(e)}"
        logger.error(f"{LOG_PREFIX} 未知错误: {e}", exc_info=True)
        return ChatResponse(
            success=False,
            content=error_message,
            error_message=error_message
        )


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
async def chat(query: str, username: str) -> str:
    """
    聊天主函数
    
    Args:
        query: 用户查询内容
        username: 用户名
        
    Returns:
        str: 聊天回复内容或错误信息
    """
    # 清理输入
    query = query.strip()
    if not query:
        return "请输入有效的查询内容"
    
    # 验证配置
    if not config.api_key:
        return "API密钥未配置"
    
    if not config.base_url:
        return "API基础URL未配置"
    
    # 构建请求
    headers = build_request_headers()
    payload = build_request_payload(query, username)
    
    # 发送请求
    chat_response = await make_chat_request(payload, headers)
    
    # 处理响应
    if chat_response.success:
        # 保存对话上下文
        save_conversation_context(username, query, chat_response.content)
        return chat_response.content
    else:
        return chat_response.content