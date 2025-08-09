import os
import logging
import json
import ast
import time

from collections import deque
from typing import Optional, Dict, Any, List


from notifyhub.plugins.utils import get_plugin_config

logger = logging.getLogger(__name__)

class chatBotConfig:
    """ChatBot配置管理"""
    PLUGIN_ID = "chatbot"
    
    def __init__(self):
        self._config_cache = None
        self._last_fetch_time = 0
        self._cache_ttl = 30  # 缓存30秒，避免频繁数据库查询
    
    def _fetch_config(self) -> Optional[Dict[str, Any]]:
        """
        从数据库获取最新配置
        
        Returns:
            Optional[Dict]: 插件配置，如果不存在返回None
        """
        try:
            config = get_plugin_config(self.PLUGIN_ID)
            return config
        except Exception as e:
            logger.error(f"获取ChatBot配置失败: {e}")
            return None
    
    def _get_config_with_cache(self) -> Optional[Dict[str, Any]]:
        """
        获取配置（带缓存机制）
        
        Returns:
            Optional[Dict]: 配置信息，如果不存在返回None
        """
        current_time = time.time()
        
        # 检查缓存是否过期
        if (self._config_cache is None or 
            current_time - self._last_fetch_time > self._cache_ttl):
            
            # 从数据库获取最新配置
            config_data = self._fetch_config()
            if config_data:
                try:
                    self._config_cache = config_data
                    self._last_fetch_time = current_time
                except (ValueError, SyntaxError) as e:
                    logger.error(f"解析ChatBot配置失败: {e}")
                    return None
            else:
                self._config_cache = None
                self._last_fetch_time = current_time
        
        return self._config_cache
    
    def get_config(self) -> Optional[Dict[str, Any]]:
        """
        获取ChatBot配置
        
        Returns:
            Optional[Dict]: 配置信息，如果不存在返回None
        """
        return self._get_config_with_cache()
    
    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值的通用方法
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            Any: 配置值或默认值
        """
        config = self._get_config_with_cache()
        if config is None:
            return default
        return config.get(key, default)
        
    @property
    def base_url(self) -> Optional[str]:
        """获取API基础URL"""
        return self._get_config_value("base_url", "https://api.openai.com")
    
    @property
    def api_key(self) -> Optional[str]:
        """获取API密钥"""
        return self._get_config_value("api_key", "")
    
    @property
    def model(self) -> Optional[str]:
        """获取模型"""
        return self._get_config_value("model", "")
    
    @property
    def proxy(self) -> Optional[str]:
        """获取代理"""
        return self._get_config_value("proxy", None)
    
    @property
    def context_num(self) -> Optional[int]:
        """获取上下文数量"""
        value = self._get_config_value("context_num", 0)
        try:
            return int(value) if value is not None else 0
        except (ValueError, TypeError):
            logger.warning(f"无效的context_num值: {value}，使用默认值0")
            return 0
    
    @property
    def custom_prompt(self) -> Optional[str]:
        """获取自定义提示"""
        return self._get_config_value("custom_prompt", "")
    
    @property
    def qywx_base_url(self) -> Optional[str]:
        """获取企业微信基础URL"""
        return self._get_config_value("qywx_base_url", "https://qyapi.weixin.qq.com")
    
    @property
    def sCorpID(self) -> Optional[str]:
        """获取企业微信ID"""
        return self._get_config_value("sCorpID", "")
    
    @property
    def sCorpsecret(self) -> Optional[str]:
        """获取企业微信secret"""
        return self._get_config_value("sCorpsecret", "")
    
    @property
    def sAgentid(self) -> Optional[str]:
        """获取企业微信agentid"""
        return self._get_config_value("sAgentid", "")
    
    @property
    def sToken(self) -> Optional[str]:
        """获取企业微信token"""
        return self._get_config_value("sToken", "")
    
    @property
    def sEncodingAESKey(self) -> Optional[str]:
        """获取企业微信EncodingAESKey"""
        return self._get_config_value("sEncodingAESKey", "")
    
    def validate_config(self) -> Dict[str, bool]:
        """
        验证配置完整性
        
        Returns:
            Dict[str, bool]: 各配置项的验证结果
        """
        validation_result = {
            'base_url': bool(self.base_url),
            'api_key': bool(self.api_key),
            'model': bool(self.model),
            'qywx_base_url': bool(self.qywx_base_url),
            'sCorpID': bool(self.sCorpID),
            'sCorpsecret': bool(self.sCorpsecret),
            'sAgentid': bool(self.sAgentid),
            'sToken': bool(self.sToken),
            'sEncodingAESKey': bool(self.sEncodingAESKey),
        }
        
        return validation_result
    
    def get_missing_configs(self) -> List[str]:
        """
        获取缺失的配置项
        
        Returns:
            List[str]: 缺失的配置项列表
        """
        validation_result = self.validate_config()
        missing_configs = [key for key, valid in validation_result.items() if not valid]
        return missing_configs


# 全局配置实例
config = chatBotConfig()

class UserRecords:
    def __init__(self, filename='context.json'):
        self.records = {}
        self.max_records = config.context_num
        self.filename = os.path.join(os.environ.get("WORKDIR"), "conf", "context.json")
        if not os.path.exists(self.filename):
            open(self.filename, 'w').close()
        self.load_records()

    def add_record(self, username, record):
        if username not in self.records:
            self.records[username] = deque(maxlen=self.max_records)
        self.records[username].append(record)
        self.save_records()

    def get_records(self, username):
        return list(self.records.get(username, []))

    def clear_records(self, username):
        if username in self.records:
            del self.records[username]
            self.save_records()

    def save_records(self):
        records_to_save = {user: list(records) for user, records in self.records.items()}
        with open(self.filename, 'w') as file:
            file.write(json.dumps(records_to_save, ensure_ascii=False, indent=4))

    def load_records(self):
        try:
            with open(self.filename, 'r') as file:
                file_content = file.read().strip()
                if file_content:
                    records_from_file = json.loads(file_content)
                    self.records = {user: deque(records, maxlen=self.max_records) for user, records in records_from_file.items()}
        except FileNotFoundError:
            pass
