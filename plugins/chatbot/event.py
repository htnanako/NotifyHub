import os
import datetime
import threading
import httpx
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from cacheout import Cache
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response
from xml.etree.ElementTree import fromstring
from tenacity import wait_random_exponential, stop_after_attempt, retry

from notifyhub.plugins.components.qywx_Crypt.WXBizMsgCrypt import WXBizMsgCrypt
from notifyhub.plugins.chatbot.utils import config, UserRecords
from notifyhub.plugins.chatbot.chatapi import chat
from notifyhub.plugins.chatbot.constants import (
    APP_USER_AGENT, CLEAR_CONTEXT_COMMANDS, TOKEN_EXPIRE_BUFFER,
    TOKEN_RETRY_ATTEMPTS, TOKEN_RETRY_MIN_WAIT, TOKEN_RETRY_MAX_WAIT,
    HTTP_TIMEOUT, ERROR_MESSAGES, SUCCESS_MESSAGES, XML_TEMPLATES, LOG_PREFIX
)
from notifyhub.common.response import json_500

# 日志记录器
logger = logging.getLogger(__name__)

# Token缓存
token_cache = Cache(maxsize=1)

# FastAPI路由器
qywx_chatbot_router = APIRouter()


@dataclass
class QywxMessage:
    """企业微信消息数据类"""
    content: str
    from_user: str
    to_user: str
    create_time: str
    msg_type: str
    msg_id: str


class QywxMessageSender:
    """企业微信消息发送器"""
    
    def __init__(self):
        self.base_url = config.qywx_base_url
        self.corpid = config.sCorpID
        self.corpsecret = config.sCorpsecret
        self.agentid = config.sAgentid
    
    @retry(stop=stop_after_attempt(TOKEN_RETRY_ATTEMPTS), wait=wait_random_exponential(min=TOKEN_RETRY_MIN_WAIT, max=TOKEN_RETRY_MAX_WAIT))
    def get_access_token(self) -> Optional[str]:
        """
        获取企业微信访问令牌
        
        Returns:
            Optional[str]: 访问令牌，获取失败返回None
        """
        # 检查缓存中的token是否有效
        cached_token = token_cache.get('access_token')
        expires_time = token_cache.get('expires_time')
        
        if (expires_time is not None and 
            expires_time >= datetime.datetime.now() and 
            cached_token):
            return cached_token
        
        if not all([self.corpid, self.corpsecret]):
            logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['config_error']}")
            return None
        
        # 重新获取token
        try:
            response = httpx.get(
                f"{self.base_url.strip('/')}/cgi-bin/gettoken",
                params={
                    'corpid': self.corpid,
                    'corpsecret': self.corpsecret
                },
                headers={'user-agent': APP_USER_AGENT},
                timeout=HTTP_TIMEOUT
            )
            
            result = response.json()
            if result.get('errcode') == 0:
                access_token = result['access_token']
                expires_in = result['expires_in']
                
                # 计算过期时间（提前500秒刷新）
                expires_time = datetime.datetime.now() + datetime.timedelta(
                    seconds=expires_in - TOKEN_EXPIRE_BUFFER
                )
                
                # 缓存token和过期时间
                token_cache.set('access_token', access_token, ttl=expires_in - TOKEN_EXPIRE_BUFFER)
                token_cache.set('expires_time', expires_time, ttl=expires_in - TOKEN_EXPIRE_BUFFER)
                
                # logger.info(f"{LOG_PREFIX} {SUCCESS_MESSAGES['token_success']}")
                return access_token
            else:
                logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['token_failed']}: {result}")
                return None
                
        except Exception as e:
            logger.error(f"{LOG_PREFIX} 获取企业微信访问令牌异常: {e}", exc_info=True)
            return None
    
    @retry(stop=stop_after_attempt(TOKEN_RETRY_ATTEMPTS), wait=wait_random_exponential(min=TOKEN_RETRY_MIN_WAIT, max=TOKEN_RETRY_MAX_WAIT))
    def _send_message(self, access_token: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送消息到企业微信
        
        Args:
            access_token: 访问令牌
            message_data: 消息数据
            
        Returns:
            Dict[str, Any]: 发送结果
        """
        try:
            url = f"{self.base_url.strip('/')}/cgi-bin/message/send"
            params = {'access_token': access_token}
            
            response = httpx.post(
                url,
                params=params,
                json=message_data,
                headers={'user-agent': APP_USER_AGENT},
                timeout=HTTP_TIMEOUT
            )
            
            return response.json()
            
        except Exception as e:
            logger.error(f"{LOG_PREFIX} 发送企业微信消息异常: {e}", exc_info=True)
            return {'errcode': -1, 'errmsg': str(e)}
    
    def send_text_message(self, text: str, to_user: str) -> bool:
        """
        发送文本消息
        
        Args:
            text: 消息内容
            to_user: 接收用户ID
            
        Returns:
            bool: 发送是否成功
        """
        access_token = self.get_access_token()
        if not access_token:
            logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['token_failed']}")
            return False
        
        message_data = {
            'touser': to_user,
            'agentid': self.agentid,
            'msgtype': 'text',
            'text': {'content': text}
        }
        
        result = self._send_message(access_token, message_data)
        
        if result.get('errcode') == 0:
            # logger.info(f"{LOG_PREFIX} {SUCCESS_MESSAGES['message_sent']}: {to_user}")
            return True
        else:
            logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['message_send_failed']}: {result}")
            return False


class QywxMessageProcessor:
    """企业微信消息处理器"""
    
    def __init__(self):
        # self.message_sender = QywxMessageSender()
        self.user_records = UserRecords()
        self._crypto = None
    
    def _get_crypto(self) -> WXBizMsgCrypt:
        """
        获取加密组件实例（按需创建）
        
        Returns:
            WXBizMsgCrypt: 加密组件实例
            
        Raises:
            ValueError: 当配置参数缺失时抛出异常
        """
        if self._crypto is None:
            # 验证配置参数
            if not all([config.sToken, config.sEncodingAESKey, config.sCorpID]):
                raise ValueError(ERROR_MESSAGES['crypto_config_incomplete'])
            
            self._crypto = WXBizMsgCrypt(
                config.sToken,
                config.sEncodingAESKey,
                config.sCorpID
            )
        return self._crypto
    
    def _parse_xml_message(self, xml_data: str) -> QywxMessage:
        """
        解析XML消息
        
        Args:
            xml_data: XML格式的消息数据
            
        Returns:
            QywxMessage: 解析后的消息对象
        """
        try:
            root = fromstring(xml_data)
            message_data = {node.tag: node.text for node in root}
            
            return QywxMessage(
                content=message_data.get('Content', ''),
                from_user=message_data.get('FromUserName', ''),
                to_user=message_data.get('ToUserName', ''),
                create_time=message_data.get('CreateTime', ''),
                msg_type=message_data.get('MsgType', ''),
                msg_id=message_data.get('MsgId', '')
            )
        except Exception as e:
            logger.error(f"解析XML消息失败: {e}", exc_info=True)
            raise ValueError("消息格式错误")
    
    def _is_clear_context_command(self, content: str) -> bool:
        """
        判断是否为清除上下文命令
        
        Args:
            content: 消息内容
            
        Returns:
            bool: 是否为清除命令
        """
        return any(content.startswith(cmd) for cmd in CLEAR_CONTEXT_COMMANDS)
    
    def _create_reply_xml(self, message: QywxMessage, content: str) -> str:
        """
        创建回复XML
        
        Args:
            message: 原始消息
            content: 回复内容
            
        Returns:
            str: XML格式的回复
        """
        return XML_TEMPLATES["reply"].format(
            to_user=message.to_user,
            from_user=message.from_user,
            create_time=message.create_time,
            msg_type=message.msg_type,
            content=content,
            msg_id=message.msg_id,
            agent_id=config.sAgentid
        )
    
    def process_message(self, encrypted_msg: str, msg_signature: str, 
                       timestamp: str, nonce: str) -> str:
        """
        处理企业微信消息
        
        Args:
            encrypted_msg: 加密的消息
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数
            
        Returns:
            str: 加密的回复消息
        """
        try:
            # 解密消息
            crypto = self._get_crypto()
            ret, decrypted_msg = crypto.DecryptMsg(
                encrypted_msg, msg_signature, timestamp, nonce
            )
            
            if ret != 0:
                logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['decrypt_failed']}: {decrypted_msg}")
                raise ValueError(ERROR_MESSAGES['decrypt_failed'])
            
            # 解析消息
            message = self._parse_xml_message(decrypted_msg.decode('utf-8'))
            
            # 处理清除上下文命令
            if self._is_clear_context_command(message.content):
                self.user_records.clear_records(message.from_user)
                reply_content = SUCCESS_MESSAGES['context_cleared']
            else:
                # 异步处理聊天消息
                self._process_chat_message_async(message)
                reply_content = f"{SUCCESS_MESSAGES['thinking']}[{config.model}]"
            
            # 创建回复XML
            reply_xml = self._create_reply_xml(message, reply_content)
            
            # 加密回复
            ret, encrypted_reply = crypto.EncryptMsg(reply_xml, nonce, timestamp)
            
            if ret != 0:
                logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['encrypt_failed']}: {encrypted_reply}")
                raise ValueError(ERROR_MESSAGES['encrypt_failed'])
            
            return encrypted_reply
            
        except Exception as e:
            logger.error(f"{LOG_PREFIX} 处理企业微信消息失败: {e}", exc_info=True)
            raise
    
    def _process_chat_message_async(self, message: QywxMessage):
        """
        异步处理聊天消息
        
        Args:
            message: 消息对象
        """
        thread = QywxChatThread(message)
        thread.start()


class QywxChatThread(threading.Thread):
    """企业微信聊天处理线程"""
    
    def __init__(self, message: QywxMessage):
        super().__init__()
        self.name = "QywxChatThread"
        self.message = message
        self.message_sender = QywxMessageSender()
        self.max_length = 768

    def split_text(self, text: str) -> list:
        """将文本按指定长度分段"""
        if len(text) <= self.max_length:
            return [text]
        
        segments = []
        current_pos = 0
        while current_pos < len(text):
            # 如果剩余文本长度小于最大长度，直接添加
            if len(text) - current_pos <= self.max_length:
                segments.append(text[current_pos:])
                break
            
            # 找到合适的分段点（在最大长度范围内）
            split_pos = current_pos + self.max_length
            # 尝试在句号、问号、感叹号处分段
            for punct in ['。', '！', '？', '.', '!', '?']:
                pos = text.rfind(punct, current_pos, split_pos)
                if pos != -1:
                    split_pos = pos + 1
                    break
            
            segments.append(text[current_pos:split_pos].strip())
            current_pos = split_pos
        return segments
    
    def run(self):
        """线程执行方法"""
        try:
            async def process():
                # 调用聊天API
                result = await chat(
                    query=self.message.content, 
                    username=self.message.from_user
                )

                # 分段发送消息
                segments = self.split_text(result)
                for segment in segments:
                    success = self.message_sender.send_text_message(segment, self.message.from_user)
                    if not success:
                        logger.error(f"{LOG_PREFIX} 发送消息失败: {self.message.from_user}")
                    await asyncio.sleep(1)

            asyncio.run(process())
            
        except Exception as e:
            logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['chat_failed']}: {e}", exc_info=True)
            # 发送错误提示
            error_msg = ERROR_MESSAGES['chat_failed']
            self.message_sender.send_text_message(error_msg, self.message.from_user)


class QywxCallbackHandler:
    """企业微信回调处理器"""
    
    def __init__(self):
        self._crypto = None
        self.message_processor = QywxMessageProcessor()
    
    def _get_crypto(self) -> WXBizMsgCrypt:
        """
        获取加密组件实例（按需创建）
        
        Returns:
            WXBizMsgCrypt: 加密组件实例
            
        Raises:
            ValueError: 当配置参数缺失时抛出异常
        """
        if self._crypto is None:
            # 验证配置参数
            if not all([config.sToken, config.sEncodingAESKey, config.sCorpID]):
                raise ValueError(ERROR_MESSAGES['crypto_config_incomplete'])
            
            self._crypto = WXBizMsgCrypt(
                config.sToken,
                config.sEncodingAESKey,
                config.sCorpID
            )
        return self._crypto
    
    def verify_url(self, msg_signature: str, timestamp: str, 
                   nonce: str, echostr: str) -> str:
        """
        验证回调URL
        
        Args:
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数
            echostr: 验证字符串
            
        Returns:
            str: 验证结果
        """
        try:
            crypto = self._get_crypto()
            ret, echo_str = crypto.VerifyURL(
                msg_signature, timestamp, nonce, echostr
            )
            
            if ret == 0:
                logger.info(f"{LOG_PREFIX} {SUCCESS_MESSAGES['url_verified']}: {echo_str.decode('utf-8')}")
                return echo_str.decode('utf-8')
            else:
                logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['url_verify_failed']}: {echo_str}")
                raise ValueError(ERROR_MESSAGES['url_verify_failed'])
                
        except Exception as e:
            logger.error(f"{LOG_PREFIX} 企业微信URL验证异常: {e}", exc_info=True)
            raise
    
    def handle_message(self, encrypted_msg: str, msg_signature: str,
                      timestamp: str, nonce: str) -> str:
        """
        处理接收到的消息
        
        Args:
            encrypted_msg: 加密的消息
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数
            
        Returns:
            str: 加密的回复消息
        """
        return self.message_processor.process_message(
            encrypted_msg, msg_signature, timestamp, nonce
        )


# 全局处理器实例
callback_handler = QywxCallbackHandler()


@qywx_chatbot_router.get("/chat")
async def verify_callback(request: Request):
    """
    企业微信回调URL验证接口
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        Response: 验证结果
    """
    try:
        # 获取验证参数
        msg_signature = request.query_params.get('msg_signature')
        timestamp = request.query_params.get('timestamp')
        nonce = request.query_params.get('nonce')
        echostr = request.query_params.get('echostr')
        
        # 验证必要参数
        if not all([msg_signature, timestamp, nonce, echostr]):
            logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['missing_params']}")
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES['missing_params'])
        
        # 执行验证
        try:
            result = callback_handler.verify_url(msg_signature, timestamp, nonce, echostr)
            return int(result)
        except ValueError as e:
            logger.error(f"{LOG_PREFIX} 配置错误: {e}")
            raise HTTPException(status_code=500, detail=ERROR_MESSAGES['config_error'])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} 企业微信回调验证失败: {e}", exc_info=True)
        return json_500(ERROR_MESSAGES['server_error'])


@qywx_chatbot_router.post("/chat")
async def receive_message(request: Request):
    """
    企业微信消息接收接口
    
    Args:
        request: FastAPI请求对象
        
    Returns:
        Response: 加密的回复消息
    """
    try:
        # 获取消息参数
        msg_signature = request.query_params.get('msg_signature')
        timestamp = request.query_params.get('timestamp')
        nonce = request.query_params.get('nonce')
        
        # 验证必要参数
        if not all([msg_signature, timestamp, nonce]):
            logger.error(f"{LOG_PREFIX} {ERROR_MESSAGES['missing_params']}")
            raise HTTPException(status_code=400, detail=ERROR_MESSAGES['missing_params'])
        
        # 获取请求体
        body = await request.body()
        encrypted_msg = body.decode('utf-8')
        
        # 处理消息
        try:
            result = callback_handler.handle_message(
                encrypted_msg, msg_signature, timestamp, nonce
            )
            return Response(content=result, media_type="text/plain")
        except ValueError as e:
            logger.error(f"{LOG_PREFIX} 配置错误: {e}")
            raise HTTPException(status_code=500, detail=ERROR_MESSAGES['config_error'])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_PREFIX} 企业微信消息处理失败: {e}", exc_info=True)
        return json_500(ERROR_MESSAGES['server_error'])
