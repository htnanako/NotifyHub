"""
ChatBot插件常量定义
"""

# 日志前缀
LOG_PREFIX = "「ChatBot」"

# HTTP相关常量
DEFAULT_TIMEOUT = 180

# 模型相关常量
O1_MODEL_PREFIX = "o1"
SYSTEM_ROLE = "system"
USER_ROLE = "user"
ASSISTANT_ROLE = "assistant"

# HTTP错误码映射
ERROR_CODE = {
    400: '[ERROR: 400] 后端服务出错，请查看日志。 | Backend service error, please check the log',
    401: '[ERROR: 401] 提供错误的API密钥 | Incorrect API key provided',
    403: '[ERROR: 403] 服务器拒绝访问，请稍后再试 | Server refused to access, please try again later',
    429: '[ERROR: 429] 额度不足 | Quota exhausted',
    502: '[ERROR: 502] 错误的网关 | Bad Gateway',
    503: '[ERROR: 503] 服务器繁忙，请稍后再试 | Server is busy, please try again later',
    504: '[ERROR: 504] 网关超时 | Gateway Time-out',
    500: '[ERROR: 500] 服务器内部错误，请稍后再试 | Internal Server Error',
}

# 企业微信相关常量
APP_USER_AGENT = "NotifyHub-ChatBot/1.0"
CLEAR_CONTEXT_COMMANDS = ['重来', '重置','重新开始']
TOKEN_EXPIRE_BUFFER = 500  # 提前500秒刷新token
TOKEN_RETRY_ATTEMPTS = 3
TOKEN_RETRY_MIN_WAIT = 1
TOKEN_RETRY_MAX_WAIT = 20
HTTP_TIMEOUT = 30

# 错误消息
ERROR_MESSAGES = {
    'token_failed': '获取企业微信访问令牌失败',
    'message_send_failed': '发送企业微信消息失败',
    'decrypt_failed': '消息解密失败',
    'encrypt_failed': '消息加密失败',
    'crypto_config_incomplete': '企业微信加密配置不完整',
    'url_verify_failed': '企业微信URL验证失败',
    'missing_params': '缺少必要参数',
    'config_error': '配置错误',
    'server_error': '服务器内部错误',
    'chat_failed': '聊天处理失败，请查看日志'
}

# 成功消息
SUCCESS_MESSAGES = {
    'token_success': '获取企业微信访问令牌成功',
    'message_sent': '企业微信消息发送成功',
    'url_verified': '企业微信URL验证成功',
    'thinking': '正在思考中，请稍候...',
    'context_cleared': '对话上下文已清除'
}

# XML模板
XML_TEMPLATES = {
    "reply": """<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{create_time}</CreateTime>
<MsgType><![CDATA[{msg_type}]]></MsgType>
<Content><![CDATA[{content}]]></Content>
<MsgId>{msg_id}</MsgId>
<AgentID>{agent_id}</AgentID>
</xml>"""
}