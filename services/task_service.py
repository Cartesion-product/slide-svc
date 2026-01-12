"""任务管理服务模块

提供任务创建、删除、查询和队列管理功能。
"""
import logging
import uuid
from typing import Optional, List, Tuple, Dict, Any
from functools import lru_cache

from config.settings import get_settings
from common.enums import AgentTypeEnum, TaskStatusEnum, PaperTypeEnum
from common.constants import TASK_TITLE_POSTER, TASK_TITLE_SLIDES
from common.redis_manager import get_redis_queue_manager, RedisQueueManager
from models.entities.user_paper_result import UserPaperResult
from models.entities.system_paper_result import SystemPaperResult
from repositories.user_paper_repo import get_user_paper_repo, UserPaperRepository
from repositories.system_paper_repo import get_system_paper_repo, SystemPaperRepository
from services.minio_service import get_minio_service, MinIOService
from exception.exceptions import (
    TaskQueueFullException,
    TaskNotFoundException,
    InvalidRequestException
)

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务类

    提供任务的创建、删除、查询等业务逻辑。
    """

    def __init__(
        self,
        user_repo: UserPaperRepository,
        system_repo: SystemPaperRepository,
        minio_service: MinIOService,
        queue_manager: RedisQueueManager
    ):
        self._user_repo = user_repo
        self._system_repo = system_repo
        self._minio_service = minio_service
        self._queue_manager = queue_manager
        self._settings = get_settings()

    def create_task(
        self,
        paper_id: str,
        source: str,
        paper_type: str,
        agent_type: str,
        user_id: str,
        title: Optional[str] = None,
        style: str = "doraemon",
        language: str = "ZH",
        density: str = "medium"
    ) -> Dict[str, Any]:
        """创建任务

        业务逻辑（根据接口设计）:
        1. 检查任务队列容量
        2. 检查系统论文是否有默认结果
        3. 创建任务记录
        4. 根据队列状态决定执行策略

        Args:
            paper_id: 论文ID
            source: 论文来源
            paper_type: 论文类型 (system/user)
            agent_type: 任务类型 (poster/slides)
            user_id: 用户ID
            title: 任务标题（可选）
            style: 风格
            language: 语言
            density: 密度

        Returns:
            创建的任务信息

        Raises:
            TaskQueueFullException: 任务队列已满
        """
        # 检查队列状态并决定执行策略
        action = self._check_queue_capacity()

        # 生成任务ID
        result_id = str(uuid.uuid4())

        # 生成标题
        if title is None:
            title = TASK_TITLE_POSTER if agent_type == AgentTypeEnum.POSTER.value else TASK_TITLE_SLIDES

        # 初始化update_system标记
        update_system = False

        # 检查系统论文是否有默认结果
        if paper_type == PaperTypeEnum.SYSTEM.value:
            default_result = self._system_repo.get_default_result(paper_id, agent_type, source)

            if default_result:
                # 系统有记录
                if default_result.file_path:
                    # 有默认结果
                    # 检查用户之前是否创建过同论文同类型的任务
                    user_has_task = self._user_repo.has_user_task(
                        user_id=user_id,
                        paper_id=paper_id,
                        source=source,
                        agent_type=agent_type
                    )

                    if user_has_task:
                        # 用户之前创建过，重新生成
                        update_system = False
                        logger.info(f"用户重新生成任务: {result_id}, update_system={update_system}")
                    else:
                        # 用户第一次创建，直接使用默认结果
                        task = UserPaperResult.create(
                            result_id=result_id,
                            agent_type=agent_type,
                            paper_id=paper_id,
                            source=source,
                            paper_type=paper_type,
                            user_id=user_id,
                            title=title,
                            style=style,
                            language=language,
                            density=density
                        )
                        task.mark_success(
                            file_path=default_result.file_path,
                            images=default_result.images
                        )
                        self._user_repo.insert(task)
                        logger.info(f"使用默认结果: {result_id}")
                        return {
                            "task_id": result_id
                        }
                else:
                    # 有记录但无file_path，重新生成
                    update_system = False
                    logger.info(f"系统记录无file_path，重新生成: {result_id}, update_system={update_system}")
            else:
                # 系统无记录，创建空记录
                self._system_repo.insert_empty_record(
                    paper_id=paper_id,
                    source=source,
                    agent_type=agent_type
                )
                update_system = True
                logger.info(f"{paper_id} 系统无记录，创建空记录: {result_id}, update_system={update_system}")
        else:
            # 用户论文，不更新系统记录
            update_system = False

        # 创建任务实体
        task = UserPaperResult.create(
            result_id=result_id,
            agent_type=agent_type,
            paper_id=paper_id,
            source=source,
            paper_type=paper_type,
            user_id=user_id,
            title=title,
            style=style,
            language=language,
            density=density
        )

        # 保存到数据库
        self._user_repo.insert(task)
        logger.info(f"任务已创建: {result_id}, update_system={update_system}")

        # 根据队列状态决定执行策略
        if action == "run_now":
            # 立即运行
            task.mark_running()
            self._user_repo.update_task(task)
            self._queue_manager.increment_running()

            self._submit_to_celery(
                result_id=result_id,
                paper_id=paper_id,
                source=source,
                paper_type=paper_type,
                agent_type=agent_type,
                user_id=user_id,
                style=style,
                language=language,
                density=density,
                update_system=update_system
            )

            logger.info(f"任务立即执行: {result_id}")
        else:
            # 进入等待队列
            if not self._queue_manager.add_to_waiting_queue(result_id):
                raise TaskQueueFullException("添加到等待队列失败")

            # 任务保持waiting状态
            logger.info(f"任务进入等待队列: {result_id}")

        return {
            "task_id": result_id
        }

    def _check_queue_capacity(self) -> str:
        """检查队列容量并决定任务执行策略

        Returns:
            "run_now" - 可以立即运行
            "wait_in_queue" - 需要进入等待队列

        Raises:
            TaskQueueFullException: 等待队列已满
        """
        # 使用Redis查询队列状态（性能优化）
        if self._queue_manager.can_run_now():
            return "run_now"

        # 运行中已满，检查等待队列
        waiting_count = len(self._queue_manager.get_waiting_queue())
        max_waiting = self._settings.max_waiting_tasks

        if waiting_count >= max_waiting:
            raise TaskQueueFullException(
                f"任务队列已满，请稍后重试。"
                f"等待中: {waiting_count}/{max_waiting}"
            )

        return "wait_in_queue"

    def schedule_from_waiting_queue(self) -> None:
        """从等待队列调度下一个任务

        如果运行中任务数未满，从等待队列取出任务并提交到Celery。
        """
        if not self._queue_manager.can_run_now():
            return

        task_id = self._queue_manager.schedule_next()
        if not task_id:
            return

        # 获取任务信息
        task = self._user_repo.find_by_result_id(task_id)
        if task is None:
            logger.warning(f"等待队列中的任务不存在: {task_id}")
            return

        if task.status != TaskStatusEnum.WAITING.value:
            logger.warning(f"等待队列中的任务状态异常: {task_id}, status={task.status}")
            return

        # 提交到Celery
        task.mark_running()
        self._user_repo.update_task(task)
        self._queue_manager.increment_running()

        # 使用保存的参数重新提交任务
        self._submit_to_celery(
            result_id=task.result_id,
            paper_id=task.paper_id,
            source=task.source,
            paper_type=task.paper_type,
            agent_type=task.agent_type,
            user_id=task.user_id,
            style=task.style,
            language=task.language,
            density=task.density,
            update_system=task.update_system
        )

        logger.info(f"成功调度任务: {task_id}, update_system={task.update_system}")

    def _submit_to_celery(
        self,
        result_id: str,
        paper_id: str,
        source: str,
        paper_type: str,
        agent_type: str,
        user_id: str,
        style: str,
        language: str,
        density: str,
        update_system: bool
    ) -> None:
        """提交任务到 Celery 队列

        Args:
            result_id: 任务ID
            paper_id: 论文ID
            source: 论文来源
            paper_type: 论文类型
            agent_type: 任务类型
            user_id: 用户ID
            style: 风格
            language: 语言
            density: 密度
            update_system: 是否更新系统记录
        """
        from celery_app.tasks import generate_slides_task

        generate_slides_task.apply_async(
            args=[],
            kwargs={
                "result_id": result_id,
                "paper_id": paper_id,
                "source": source,
                "paper_type": paper_type,
                "agent_type": agent_type,
                "user_id": user_id,
                "style": style,
                "language": language,
                "density": density,
                "update_system": update_system
            },
            task_id=result_id,
            queue="slides"
        )
        logger.info(f"任务已提交到队列: {result_id}, update_system={update_system}")

    def delete_task(self, task_id: str, user_id: str) -> bool:
        """删除任务

        如果任务正在运行，会先尝试取消。

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            是否删除成功

        Raises:
            TaskNotFoundException: 任务不存在
        """
        task = self._user_repo.find_by_result_id(task_id)
        if task is None:
            raise TaskNotFoundException(task_id)

        # 验证所有权
        if task.user_id != user_id:
            raise TaskNotFoundException(task_id)

        # 如果任务正在运行，先取消
        if task.status == TaskStatusEnum.RUNNING.value:
            from celery_app.celery_config import celery_app
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"已取消运行中的任务: {task_id}")

            # 减少运行中计数并触发调度
            self._queue_manager.decrement_running()
            self.schedule_from_waiting_queue()

        # 从等待队列中移除（如果在等待队列中）
        if task.status == TaskStatusEnum.WAITING.value:
            self._queue_manager.schedule_next()

        # 删除数据库记录（不删除 MinIO 中的文件，不影响系统论文默认结果）
        self._user_repo.delete_task(task_id)
        logger.info(f"任务已删除: {task_id}")

        return True

    def get_task_detail(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """获取任务详情

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            任务详情字典

        Raises:
            TaskNotFoundException: 任务不存在
        """
        task = self._user_repo.find_by_result_id(task_id)
        if task is None or task.user_id != user_id:
            raise TaskNotFoundException(task_id)

        result = {
            "task_id": task.result_id,
            "title": task.title,
            "agent_type": task.agent_type,
            "status": task.status,
            "error_reason": task.error_reason,
            "file_path": task.file_path,
            "image_urls": task.images or [],
            "start_time": task.start_time.isoformat() if task.start_time else None,
            "end_time": task.end_time.isoformat() if task.end_time else None,
            "created_time": task.created_time.isoformat() if task.created_time else None,
            "paper_id": task.paper_id,
            "source": task.source
        }

        return result

    def get_task_download(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """获取任务下载链接

        Args:
            task_id: 任务ID
            user_id: 用户ID

        Returns:
            下载信息 {"file_path": "", "expires_in": 3600}

        Raises:
            TaskNotFoundException: 任务不存在
        """
        task = self._user_repo.find_by_result_id(task_id)
        if task is None or task.user_id != user_id:
            raise TaskNotFoundException(task_id)

        if task.status != TaskStatusEnum.SUCCESS.value or not task.file_path:
            raise InvalidRequestException("任务未完成或无结果文件")

        # 解析桶名和对象名
        file_path = task.file_path
        if "/" in file_path:
            parts = file_path.split("/", 1)
            bucket_name = parts[0]
            object_name = parts[1]
        else:
            raise InvalidRequestException("无效的文件路径格式")

        # 生成预签名 URL
        expires = 3600  # 1小时
        url = self._minio_service.get_file_url(bucket_name, object_name, expires)

        return {
            "file_path": url,
            "expires_in": expires
        }

    def list_tasks(
        self,
        user_id: str,
        paper_id: str,
        source: str,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """分页查询任务列表

        Args:
            user_id: 用户ID
            paper_id: 论文ID
            source: 论文来源
            page: 页码（0表示查询所有）
            page_size: 每页大小

        Returns:
            分页结果 {"items": [], "total": 0, "page": 1, "page_size": 10}
        """
        if page == 0:
            # 查询所有
            items, total = self._user_repo.find_by_user_and_paper(
                user_id=user_id,
                paper_id=paper_id,
                source=source,
                skip=0,
                limit=1000  # 设置一个较大的限制
            )
        else:
            skip = (page - 1) * page_size
            items, total = self._user_repo.find_by_user_and_paper(
                user_id=user_id,
                paper_id=paper_id,
                source=source,
                skip=skip,
                limit=page_size
            )

        return {
            "items": [
                {
                    "task_id": item.result_id,
                    "title": item.title,
                    "agent_type": item.agent_type,
                    "status": item.status,
                    "created_time": item.created_time.isoformat() if item.created_time else None,
                    "paper_id": item.paper_id,
                    "source": item.source
                }
                for item in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态

        Returns:
            队列状态 {"running": 0, "waiting": 0, "max_running": 2, "max_waiting": 5}
        """
        return self._queue_manager.get_queue_status()


@lru_cache()
def get_task_service() -> TaskService:
    """获取任务服务单例

    Returns:
        TaskService: 服务实例
    """
    return TaskService(
        user_repo=get_user_paper_repo(),
        system_repo=get_system_paper_repo(),
        minio_service=get_minio_service(),
        queue_manager=get_redis_queue_manager()
    )
