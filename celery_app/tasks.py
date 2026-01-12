"""Celery 任务定义

定义演示文稿生成的异步任务。
"""
import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from celery_app.celery_config import celery_app
from celery import states
from celery.exceptions import Ignore
from common.redis_manager import get_redis_queue_manager
from utilities.log_manager import get_celery_logger

# 使用 LogManager 的 Celery logger
logger = get_celery_logger()


@celery_app.task(bind=True, name="celery_app.tasks.generate_slides_task")
def generate_slides_task(
    self,
    result_id: str,
    paper_id: str,
    source: str,
    source_path: str,
    paper_type: str,
    agent_type: str,
    user_id: str,
    bucket: str = "kb-paper-parsed",
    style: str = "doraemon",
    language: str = "ZH",
    density: str = "medium",
    update_system: bool = False
) -> Dict[str, Any]:
    """生成演示文稿/全景信息图任务

    使用 LangGraph 智能体执行生成任务。

    Args:
        result_id: 任务ID
        paper_id: 论文ID
        source: 论文来源
        source_path: MinIO文件路径（包括桶名）
        paper_type: 论文类型 (system/user)
        agent_type: 任务类型 (poster/slides)
        user_id: 用户ID
        bucket: 论文解析结果桶名
        style: 风格类型
        language: 语言 (ZH/EN)
        density: 内容密度
        update_system: 是否更新系统记录

    Returns:
        任务结果字典
    """
    logger.info(f"开始执行任务: {result_id}, update_system={update_system}")

    queue_manager = get_redis_queue_manager()

    try:
        # 使用 LangGraph 智能体执行任务
        from agents.slides_agent import SlidesAgent

        agent = SlidesAgent()

        # 创建新的事件循环并运行智能体
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                agent.run(
                    result_id=result_id,
                    paper_id=paper_id,
                    source=source,
                    source_path=source_path,
                    paper_type=paper_type,
                    agent_type=agent_type,
                    user_id=user_id,
                    bucket=bucket,
                    style=style,
                    language=language,
                    density=density,
                    update_system=update_system
                )
            )
        finally:
            loop.close()

        logger.info(f"任务执行完成: {result_id}, status={result.get('status')}")

        # 检查任务状态，如果是失败则抛出异常
        if result.get("status") == "failed":
            error_msg = result.get("error_message", "任务执行失败")
            logger.error(f"任务失败: {result_id}, 错误: {error_msg}")
            # 抛出异常，让Celery自动标记任务为失败
            raise Exception(error_msg)

        # 任务成功完成
        logger.info(f"任务成功: {result_id}")

        # 任务完成，减少运行中计数并触发调度
        queue_manager.decrement_running()
        _schedule_next_task(result_id)

        return result

    except Exception as e:
        logger.error(f"任务执行异常: {result_id}, 错误: {e}", exc_info=True)

        # 标记任务失败（如果还没有标记）
        from repositories.user_paper_repo import get_user_paper_repo
        user_repo = get_user_paper_repo()
        user_repo.mark_failed(result_id, str(e))

        # 任务失败，减少运行中计数并触发调度
        queue_manager.decrement_running()
        _schedule_next_task(result_id)

        # 重新抛出异常，让Celery处理
        raise

    finally:
        # 清理临时文件
        _cleanup_temp_files(result_id)


def _schedule_next_task(completed_task_id: str) -> None:
    """调度下一个等待中的任务

    Args:
        completed_task_id: 已完成的任务ID（用于日志）
    """
    try:
        from services.task_service import get_task_service
        task_service = get_task_service()
        task_service.schedule_from_waiting_queue()
    except Exception as e:
        logger.error(f"调度下一个任务失败: {e}")


def _cleanup_temp_files(result_id: str) -> None:
    """清理临时文件

    Args:
        result_id: 任务ID
    """
    import shutil

    temp_dir = PROJECT_ROOT / "data" / "temp" / result_id
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir)
            logger.info(f"已清理临时文件: {result_id}")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {result_id}, 错误: {e}")


@celery_app.task(name="celery_app.tasks.cancel_task")
def cancel_task(result_id: str) -> bool:
    """取消任务

    Args:
        result_id: 任务ID

    Returns:
        是否成功取消
    """
    from repositories.user_paper_repo import get_user_paper_repo

    queue_manager = get_redis_queue_manager()
    user_repo = get_user_paper_repo()
    task = user_repo.find_by_result_id(result_id)

    if task is None:
        logger.warning(f"任务不存在: {result_id}")
        return False

    # 尝试撤销 Celery 任务
    celery_app.control.revoke(result_id, terminate=True, signal="SIGTERM")

    # 更新任务状态为失败
    user_repo.mark_failed(result_id, "任务已被用户取消")

    # 如果任务正在运行，减少计数并触发调度
    from common.enums import TaskStatusEnum
    if task.status == TaskStatusEnum.RUNNING.value:
        queue_manager.decrement_running()
        _schedule_next_task(result_id)

    # 清理临时文件
    _cleanup_temp_files(result_id)

    logger.info(f"任务已取消: {result_id}")
    return True
