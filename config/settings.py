"""配置管理模块

提供统一的配置管理，从 appconfig.json 加载配置和环境变量。
"""
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from functools import lru_cache


class Settings:
    """统一配置管理类

    单例模式，负责加载和管理应用配置。
    """

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / "appconfig.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = json.load(f)

    # ============ 基础配置 ============

    @property
    def port(self) -> int:
        """服务端口号"""
        return self._config.get('port', 5003)

    @property
    def mode(self) -> str:
        """运行模式: dev/prod"""
        return self._config.get('mode', 'prod')

    @property
    def is_dev(self) -> bool:
        """是否为开发模式"""
        return self.mode.lower() == 'dev'

    @property
    def log_config(self) -> Dict:
        """日志配置"""
        return self._config.get('log', {})

    # ============ MongoDB 配置 ============

    @property
    def mongo_uri(self) -> str:
        """MongoDB 连接 URI"""
        return os.getenv('KB_FRAMEWORK_DB', '')

    @property
    def mongo_database(self) -> str:
        """MongoDB 数据库名"""
        return os.getenv('SLIDES_MONGO_DB', 'slide_svc')

    @property
    def knowledge_db_name(self) -> str:
        """知识库数据库名 (Source Content)"""
        # 默认为 SV_KNOWLEDGE_DB
        return os.getenv('KNOWLEDGE_DB_NAME', 'SV_KNOWLEDGE_DB')

    @property
    def system_paper_collection(self) -> str:
        """系统论文结果集合名"""
        return os.getenv('SLIDES_SYSTEM_PAPER_COLLECTION', 'system_paper_agent_result')

    @property
    def user_paper_collection(self) -> str:
        """用户论文结果集合名"""
        return os.getenv('SLIDES_USER_PAPER_COLLECTION', 'user_paper_agent_result')

    @property
    def system_paper_content_collection(self) -> str:
        """系统论文原始内容表名 (Source Content)"""
        return os.getenv('SYSTEM_PAPER_CONTENT_COLLECTION', 'system_paper_original_content')

    # ============ Celery 配置 ============

    @property
    def celery_broker_url(self) -> str:
        """Celery Broker URL (Redis)"""
        return os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')

    @property
    def celery_result_backend(self) -> str:
        """Celery Result Backend URL"""
        return os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

    # ============ MinIO 配置 ============

    @property
    def minio_endpoint(self) -> str:
        """MinIO 服务端点"""
        return os.getenv('KB_MINIO_ENDPOINT', '')

    @property
    def minio_access_key(self) -> str:
        """MinIO 访问密钥"""
        return os.getenv('KB_MINIO_ACCESSKEY', '')

    @property
    def minio_secret_key(self) -> str:
        """MinIO 秘密密钥"""
        return os.getenv('KB_MINIO_SECRETKEY', '')

    # MinIO 多桶配置 - 按类型区分
    @property
    def system_slides_bucket(self) -> str:
        """系统 Slides 桶名"""
        return os.getenv('SYSTEM_SLIDES_MINIO_BUCKET', 'kb-slide-system')

    @property
    def user_slides_bucket(self) -> str:
        """用户 Slides 桶名"""
        return os.getenv('USER_SLIDES_MINIO_BUCKET', 'kb-slide-user')

    @property
    def system_poster_bucket(self) -> str:
        """系统 Poster 桶名"""
        return os.getenv('SYSTEM_POSTER_MINIO_BUCKET', 'kb-poster-system')

    @property
    def user_poster_bucket(self) -> str:
        """用户 Poster 桶名"""
        return os.getenv('USER_POSTER_MINIO_BUCKET', 'kb-poster-user')

    def get_bucket_name(self, agent_type: str, paper_type: str) -> str:
        """根据任务类型和论文类型获取对应的桶名

        Args:
            agent_type: 任务类型 (poster/slides)
            paper_type: 论文类型 (system/user)

        Returns:
            str: 对应的桶名
        """
        bucket_map = {
            ('slides', 'system'): self.system_slides_bucket,
            ('slides', 'user'): self.user_slides_bucket,
            ('poster', 'system'): self.system_poster_bucket,
            ('poster', 'user'): self.user_poster_bucket,
        }
        return bucket_map.get((agent_type, paper_type), self.user_slides_bucket)

    # ============ 任务队列配置 ============

    @property
    def max_running_tasks(self) -> int:
        """最大并行运行任务数"""
        return int(os.getenv('SLIDES_MAX_RUNNING_TASKS', '2'))

    @property
    def max_waiting_tasks(self) -> int:
        """最大等待队列任务数"""
        return int(os.getenv('SLIDES_MAX_WAITING_TASKS', '5'))

    @property
    def reset_waiting_on_restart(self) -> bool:
        """服务重启时是否将等待队列任务标记为失败

        - True: 将等待任务标记为失败
        - False: 保留等待任务并重新调度（默认）
        """
        return os.getenv('SLIDES_RESET_WAITING_ON_RESTART', 'false').lower() == 'true'

    # ============ LLM 配置 ============

    @property
    def llm_model(self) -> str:
        """LLM 模型名称"""
        return os.getenv('LLM_MODEL', 'gemini-3-flash')

    @property
    def llm_api_key(self) -> str:
        """LLM API 密钥"""
        return os.getenv('RAG_LLM_API_KEY', '')

    @property
    def llm_base_url(self) -> str:
        """LLM API 基础 URL"""
        return os.getenv('RAG_LLM_BASE_URL', '')

    @property
    def llm_max_tokens(self) -> int:
        """LLM 最大 token 数"""
        return int(os.getenv('RAG_LLM_MAX_TOKENS', '16000'))

    # ============ 图像生成配置 ============

    @property
    def image_gen_provider(self) -> str:
        """图像生成服务提供商"""
        return os.getenv('IMAGE_GEN_PROVIDER', 'doubao')

    @property
    def image_gen_api_key(self) -> str:
        """图像生成 API 密钥"""
        return os.getenv('IMAGE_GEN_API_KEY', '')

    @property
    def image_gen_model(self) -> str:
        """图像生成模型"""
        return os.getenv('IMAGE_GEN_MODEL', 'doubao-seedream-4-5-251128')

    # ============ 解析器配置 ============

    @property
    def parser(self) -> str:
        """文档解析器类型"""
        return os.getenv('PARSER', 'mineru')

    @property
    def parser_enabled(self) -> bool:
        """是否启用文档解析"""
        return os.getenv('PARSER_ENABLED', 'False').lower() == 'true'

    # ============ Paper2Slides 服务配置 ============

    @property
    def paper2slides_api_url(self) -> str:
        """Paper2Slides API 地址"""
        return os.getenv('PAPER2SLIDES_API_URL', 'http://localhost:5003/p2s')

    # ============ 认证配置 ============

    @property
    def auth_service_url(self) -> str:
        """认证服务 URL"""
        return os.getenv('KB_API_SERVICE_AUTHENTICATION', '')

    @property
    def global_token(self) -> str:
        """全局访问 Token"""
        return os.getenv('KB_API_SERVICE_GLOBAL_TOKEN', '')


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例

    Returns:
        Settings: 配置管理实例
    """
    return Settings()
