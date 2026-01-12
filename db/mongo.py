"""MongoDB 数据库连接模块

提供 MongoDB 连接管理和集合访问功能。
"""
import logging
from typing import Optional
from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure

from config.settings import get_settings

logger = logging.getLogger(__name__)


class MongoDBClient:
    """MongoDB 客户端管理类

    单例模式，提供数据库连接和集合访问。
    """

    _instance: Optional['MongoDBClient'] = None
    _client: Optional[MongoClient] = None
    _database: Optional[Database] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self) -> None:
        """建立数据库连接"""
        if self._client is not None:
            return

        settings = get_settings()
        try:
            self._client = MongoClient(
                settings.mongo_uri,
                maxPoolSize=50,
                minPoolSize=10,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                retryWrites=True
            )
            # 验证连接
            self._client.admin.command('ping')
            self._database = self._client[settings.mongo_database]
            logger.info(f"MongoDB 连接成功: {settings.mongo_database}")
        except ConnectionFailure as e:
            logger.error(f"MongoDB 连接失败: {e}")
            raise

    def disconnect(self) -> None:
        """关闭数据库连接"""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("MongoDB 连接已关闭")

    @property
    def database(self) -> Database:
        """获取数据库实例"""
        if self._database is None:
            self.connect()
        return self._database

    def get_collection(self, name: str) -> Collection:
        """获取集合

        Args:
            name: 集合名称

        Returns:
            Collection: MongoDB 集合实例
        """
        return self.database[name]

    @property
    def system_paper_collection(self) -> Collection:
        """系统论文结果集合"""
        settings = get_settings()
        return self.get_collection(settings.system_paper_collection)

    @property
    def user_paper_collection(self) -> Collection:
        """用户论文结果集合"""
        settings = get_settings()
        return self.get_collection(settings.user_paper_collection)

    def ensure_indexes(self) -> None:
        """确保索引存在"""
        settings = get_settings()

        # 系统论文结果集合索引
        system_collection = self.system_paper_collection
        system_collection.create_index(
            [("paper_id", 1), ("agent_type", 1), ("source", 1)],
            unique=True,
            name="uk_paper_agent"
        )
        system_collection.create_index(
            [("result_id", 1)],
            unique=True,
            name="uk_taskid"
        )
        system_collection.create_index(
            [("created_time", -1)],
            name="idx_created_time"
        )

        # 用户论文结果集合索引
        user_collection = self.user_paper_collection
        user_collection.create_index(
            [("result_id", 1)],
            unique=True,
            name="uk_taskid"
        )
        user_collection.create_index(
            [("user_id", 1), ("paper_id", 1), ("source", 1)],
            name="idx_user_paper"
        )
        user_collection.create_index(
            [("user_id", 1), ("status", 1)],
            name="idx_user_status"
        )
        user_collection.create_index(
            [("created_time", -1)],
            name="idx_created_time"
        )

        logger.info("MongoDB 索引创建完成")


@lru_cache()
def get_mongo_client() -> MongoDBClient:
    """获取 MongoDB 客户端单例

    Returns:
        MongoDBClient: MongoDB 客户端实例
    """
    client = MongoDBClient()
    client.connect()
    return client
