"""演示文稿生成智能体

基于 LangGraph 工作流，实现 Poster/Slides 的生成：
1. 参数校验节点 - 验证参数并更新任务状态为 running
2. 获取文档内容节点 - 从 SV_KNOWLEDGE_DB 查询 MD 内容并写入本地
3. 接口调用节点 - 直接调用 Paper2SlidesService 生成管道
4. 文件上传节点 - 将生成的文件上传至 MinIO
5. 用户数据更新节点 - 更新 user_paper_agent_result 表
6. 系统数据更新节点 - 更新 system_paper_agent_result 表（仅系统论文）
"""

import os
import uuid
import traceback
from pathlib import Path
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from minio.error import S3Error
from langgraph.graph import StateGraph, END

from config.settings import get_settings
from common.enums import (
    AgentTypeEnum,
    TaskStatusEnum,
    PaperTypeEnum,
    LanguageEnum
)
from services.minio_service import get_minio_service
from services.paper2slides_service import get_paper2slides_service
from repositories.user_paper_repo import get_user_paper_repo
from repositories.system_paper_repo import get_system_paper_repo
from utilities.log_manager import get_celery_logger
from db.mongo import get_mongo_client

# 使用 LogManager 的 Celery logger
logger = get_celery_logger()

# 临时文件目录
TEMP_DIR = Path(__file__).parent.parent / "data" / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


class SlidesAgentState(TypedDict):
    """智能体状态定义"""
    # 输入参数
    result_id: str
    paper_id: str
    source: str
    paper_type: str
    agent_type: str
    user_id: str
    style: str
    language: str
    density: str
    update_system: bool

    # 中间状态
    local_md_path: Optional[str]
    output_folder: Optional[str]
    output_files: Optional[List[Dict[str, str]]]

    # 结果
    file_path: Optional[str]
    images: Optional[List[str]]

    # 流程控制
    current_step: str
    status: str
    error_message: Optional[str]


class SlidesAgent:
    """演示文稿生成智能体"""

    def __init__(self):
        self._settings = get_settings()
        self._minio_service = get_minio_service()
        self._user_repo = get_user_paper_repo()
        self._system_repo = get_system_paper_repo()

        # 构建工作流
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()

    def _build_workflow(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        workflow = StateGraph(SlidesAgentState)

        # 添加节点
        workflow.add_node("validate_params", self.validate_params_node)
        workflow.add_node("get_md_content", self.get_md_content_node) # 变更名称
        workflow.add_node("call_api", self.call_api_node)
        workflow.add_node("upload_files", self.upload_files_node)
        workflow.add_node("update_user_data", self.update_user_data_node)
        workflow.add_node("update_system_data", self.update_system_data_node)

        # 设置入口点
        workflow.set_entry_point("validate_params")

        # 添加边: 线性流程
        workflow.add_edge("validate_params", "get_md_content") # 变更
        workflow.add_edge("get_md_content", "call_api")        # 变更
        workflow.add_edge("call_api", "upload_files")
        workflow.add_edge("upload_files", "update_user_data")
        workflow.add_edge("update_user_data", "update_system_data")
        workflow.add_edge("update_system_data", END)

        return workflow

    # ==================== 节点函数 ====================

    def validate_params_node(self, state: SlidesAgentState) -> SlidesAgentState:
        """参数校验节点

        验证必要参数并更新任务状态为 running
        """
        state["current_step"] = "validate_params"
        logger.info(f"[{state['result_id']}] 开始参数校验...")

        try:
            # 验证 language 参数
            language = state.get("language", LanguageEnum.ZH.value)
            if language not in (LanguageEnum.ZH.value, LanguageEnum.EN.value):
                raise ValueError(f"无效的语言参数: {language}，只支持 ZH 或 EN")

            # 验证 agent_type
            agent_type = state.get("agent_type")
            if agent_type not in (AgentTypeEnum.POSTER.value, AgentTypeEnum.SLIDES.value):
                raise ValueError(f"无效的任务类型: {agent_type}")

            # 如果language为EN，将style改为style + "_en"
            if language == LanguageEnum.EN.value:
                style = state.get("style", "academic")
                state["style"] = f"{style}_en"
                logger.info(f"[{state['result_id']}] 语言为EN，style已修改为: {state['style']}")

            # 更新任务状态为 running
            task = self._user_repo.find_by_result_id(state["result_id"])
            if task:
                task.mark_running()
                self._user_repo.update_task(task)
                logger.info(f"[{state['result_id']}] 任务状态已更新为 running")

            state["status"] = "running"

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{state['result_id']}] 参数校验失败: {error_msg}")
            state["status"] = "failed"
            state["error_message"] = error_msg
            self._mark_task_failed(
                result_id=state["result_id"],
                error_message=error_msg,
                paper_id=state.get("paper_id"),
                agent_type=state.get("agent_type"),
                source=state.get("source"),
                paper_type=state.get("paper_type"),
                update_system=state.get("update_system", False)
            )
            raise Exception(error_msg)

        return state

    def get_md_content_node(self, state: SlidesAgentState) -> SlidesAgentState:
        """获取文档内容节点 (原 download_file_node)

        从 SV_KNOWLEDGE_DB 查询 system_paper_original_content 获取 MD 内容，并写入临时文件
        """
        state["current_step"] = "get_md_content"
        logger.info(f"[{state['result_id']}] 开始获取MD文档内容...")

        try:
            paper_id = state["paper_id"]
            source = state["source"]

            # 1. 连接 Mongo 并查询内容
            mongo_client = get_mongo_client()
            collection = mongo_client.system_paper_content_collection

            logger.info(f"[{state['result_id']}] 查询系统论文: paper_id={paper_id}, source={source}")

            # 假设 source 对应 content 表的 source 字段
            doc = collection.find_one({"paper_id": paper_id, "source": source})

            if not doc:
                raise ValueError(f"未找到论文内容: paper_id={paper_id}, source={source}")

            content = doc.get("content")
            if not content:
                raise ValueError(f"论文内容为空: paper_id={paper_id}")

            # 2. 写入本地临时文件
            local_dir = TEMP_DIR / state["result_id"]
            local_dir.mkdir(parents=True, exist_ok=True)
            local_md_path = local_dir / f"{paper_id}.md"

            with open(local_md_path, "w", encoding="utf-8") as f:
                f.write(content)

            state["local_md_path"] = str(local_md_path)
            logger.info(f"[{state['result_id']}] MD内容已写入临时文件: {local_md_path}")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{state['result_id']}] 获取文档内容失败: {error_msg}")
            state["status"] = "failed"
            state["error_message"] = error_msg

            self._mark_task_failed(
                result_id=state["result_id"],
                error_message=error_msg,
                paper_id=state.get("paper_id"),
                agent_type=state.get("agent_type"),
                source=state.get("source"),
                paper_type=state.get("paper_type"),
                update_system=state.get("update_system", False)
            )
            # 再次抛出异常以通知 LangGraph 流程终止（或触发重试策略）
            raise Exception(error_msg)

        return state

    async def call_api_node(self, state: SlidesAgentState) -> SlidesAgentState:
        """接口调用节点

        直接调用 Paper2SlidesService 生成管道生成 Poster/Slides
        """
        state["current_step"] = "call_api"
        logger.info(f"[{state['result_id']}] 开始调用生成管道...")

        try:
            # 根据agent_type设置length或density
            agent_type = state["agent_type"]
            length = "medium"
            density = "medium"

            if agent_type == "slides":
                # slides类型：设置length参数（'short', 'medium', 'long'）
                density_value = state.get("density", "medium")
                level_type = {"sparse": "short", "medium": "medium", "dense": "long"}
                # 映射：sparse->short, medium->medium, dense->long
                length = level_type.get(density_value, "medium")
            else:
                # poster类型：设置density参数（'sparse', 'medium', 'dense'）
                density = state.get("density", "medium")

            # 准备文件路径
            md_file_path = state["local_md_path"]
            file_paths = [md_file_path]

            # 生成 session_id
            session_id = str(uuid.uuid4())

            # 获取服务实例并构建配置
            service = get_paper2slides_service()
            config = service.build_config(
                input_path=md_file_path,
                content_type="paper",
                output_type=agent_type,
                style=state.get("style", "academic"),
                length=length,
                density=density,
                fast_mode=True
            )

            # 直接调用服务生成
            result = await service.generate(
                session_id=session_id,
                file_paths=file_paths,
                config=config
            )

            # 从结果中获取输出文件
            output_files = result.get("output_files", [])
            if not output_files:
                raise Exception("管道返回的 output_files 为空")

            # 转换文件格式
            state["output_files"] = [
                {
                    "filename": f.get("filename"),
                    "path": f.get("path")
                }
                for f in output_files
                if f.get("filename") and f.get("path")
            ]

            # 保存 output_folder
            output_dir = result.get("output_dir")
            if output_dir:
                state["output_folder"] = output_dir

            logger.info(f"[{state['result_id']}] 生成完成，输出文件: {len(state['output_files'])} 个")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{state['result_id']}] 生成失败: {error_msg}")
            state["status"] = "failed"
            state["error_message"] = error_msg
            self._mark_task_failed(
                result_id=state["result_id"],
                error_message=error_msg,
                paper_id=state.get("paper_id"),
                agent_type=state.get("agent_type"),
                source=state.get("source"),
                paper_type=state.get("paper_type"),
                update_system=state.get("update_system", False)
            )
            raise Exception(error_msg)

        return state

    def upload_files_node(self, state: SlidesAgentState) -> SlidesAgentState:
        """文件上传节点

        将生成的文件上传至 MinIO
        """
        state["current_step"] = "upload_files"
        logger.info(f"[{state['result_id']}] 开始上传文件...")

        try:
            output_files = state.get("output_files", [])
            if not output_files:
                raise Exception("没有可上传的文件")

        # 上传文件
            result = self._minio_service.upload_task_results(
                agent_type=state["agent_type"],
                paper_type=state["paper_type"],
                paper_id=state["paper_id"],
                result_id=state['result_id'],
                source=state["source"],
                user_id=state["user_id"],
                output_files=output_files
            )

            state["file_path"] = result.get("file_path")
            state["images"] = result.get("images")

            logger.info(f"[{state['result_id']}] 文件上传完成: {state['file_path']}")

        except Exception as e:
            error_msg = f"文件上传失败: {str(e)}"
            logger.error(f"[{state['result_id']}] {error_msg}")
            state["status"] = "failed"
            state["error_message"] = error_msg
            self._mark_task_failed(
                result_id=state["result_id"],
                error_message=error_msg,
                paper_id=state.get("paper_id"),
                agent_type=state.get("agent_type"),
                source=state.get("source"),
                paper_type=state.get("paper_type"),
                update_system=state.get("update_system", False)
            )
            raise Exception(error_msg)

        return state

    def update_user_data_node(self, state: SlidesAgentState) -> SlidesAgentState:
        """用户数据更新节点

        根据update_system标记决定批量更新还是单任务更新
        """
        state["current_step"] = "update_user_data"
        logger.info(f"[{state['result_id']}] 开始更新用户数据...")

        try:
            # 更新当前任务
            task = self._user_repo.find_by_result_id(state["result_id"])
            if task:
                task.mark_success(
                    file_path=state["file_path"],
                    images=state.get("images")
                )
                self._user_repo.update_task(task)

            # 根据update_system标记决定是否批量更新
            if state["update_system"]:
                # 系统首次生成，批量更新所有running任务
                self._user_repo.update_running_tasks(
                    paper_id=state["paper_id"],
                    source=state["source"],
                    agent_type=state["agent_type"],
                    file_path=state["file_path"],
                    images=state.get("images")
                )
                logger.info(f"批量更新完成: {state['result_id']}, update_system=True")
            else:
                # 用户重新生成，只更新当前任务
                logger.info(f"只更新当前任务: {state['result_id']}, update_system=False")

            state["status"] = "success"
            logger.info(f"[{state['result_id']}] 用户数据更新完成")

        except Exception as e:
            error_msg = f"用户数据更新失败: {str(e)}"
            logger.error(f"[{state['result_id']}] {error_msg}")
            state["status"] = "failed"
            state["error_message"] = error_msg
            self._mark_task_failed(
                result_id=state["result_id"],
                error_message=error_msg,
                paper_id=state.get("paper_id"),
                agent_type=state.get("agent_type"),
                source=state.get("source"),
                paper_type=state.get("paper_type"),
                update_system=state.get("update_system", False)
            )
            raise Exception(error_msg)

        return state

    def update_system_data_node(self, state: SlidesAgentState) -> SlidesAgentState:
        """系统数据更新节点

        根据update_system标记决定是否执行更新
        """
        state["current_step"] = "update_system_data"
        logger.info(f"[{state['result_id']}] 开始更新系统数据...")

        try:
            # 只有update_system=True且系统论文才更新系统表
            if state["paper_type"] == PaperTypeEnum.SYSTEM.value and state["update_system"]:
                self._system_repo.update_file_path(
                    paper_id=state["paper_id"],
                    source=state["source"],
                    agent_type=state["agent_type"],
                    file_path=state["file_path"],
                    images=state.get("images"),
                    result_id=state["result_id"]
                )
                logger.info(f"[{state['result_id']}] 系统数据更新完成, update_system=True")
            else:
                logger.info(f"[{state['result_id']}] 跳过系统数据更新, paper_type={state['paper_type']}, update_system={state['update_system']}")

        except Exception as e:
            logger.error(f"[{state['result_id']}] 系统数据更新失败: {e}")
            # 系统数据更新失败不影响整体任务状态
            logger.warning(f"[{state['result_id']}] 系统数据更新失败，但任务仍标记为成功")

        return state

    # ==================== 辅助方法 ====================

    def _collect_output_files(self, output_folder: str) -> List[Dict[str, str]]:
        """收集输出文件

        Args:
            output_folder: 输出文件夹路径

        Returns:
            文件列表 [{"filename": "", "path": ""}]
        """
        output_files = []
        folder = Path(output_folder)

        if folder.exists():
            for file_path in folder.iterdir():
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    if suffix in (".pdf", ".png", ".jpg", ".jpeg", ".webp"):
                        output_files.append({
                            "filename": file_path.name,
                            "path": str(file_path)
                        })

        return output_files

    def _mark_task_failed(
        self,
        result_id: str,
        error_message: str,
        paper_id: str = None,
        agent_type: str = None,
        source: str = None,
        paper_type: str = None,
        update_system: bool = False
    ) -> None:
        """标记任务失败

        Args:
            result_id: 任务ID
            error_message: 错误信息
            paper_id: 论文ID（可选）
            agent_type: 任务类型（可选）
            source: 论文来源（可选）
            paper_type: 论文类型（可选）
            update_system: 是否更新系统记录（可选）
        """
        try:
            # 更新用户任务状态
            task = self._user_repo.find_by_result_id(result_id)
            if task:
                task.mark_failed(error_message)
                self._user_repo.update_task(task)
                logger.info(f"[{result_id}] 用户任务已标记为失败: {error_message}")

            # 如果是系统论文且需要更新系统记录，删除无效的系统记录
            if update_system:
                try:
                    system_result = self._system_repo.get_default_result(
                        paper_id,
                        agent_type,
                        source
                    )
                    if system_result and not system_result.file_path:
                        # 系统记录存在但没有file_path，删除系统记录
                        self._system_repo.delete_by_paper_id(
                            paper_id,
                            agent_type,
                            source
                        )
                        logger.info(
                            f"[{result_id}] 已删除无结果的系统记录: "
                            f"paper_id={paper_id}, agent_type={agent_type}, source={source}"
                        )
                except Exception as e:
                    logger.error(f"[{result_id}] 删除系统记录失败: {e}")

        except Exception as e:
            logger.error(f"[{result_id}] 标记任务失败时出错: {e}")

    # ==================== 公开接口 ====================

    async def run(
        self,
        result_id: str,
        paper_id: str,
        source: str,
        paper_type: str,
        agent_type: str,
        user_id: str,
        style: str = "doraemon",
        language: str = "ZH",
        density: str = "medium",
        update_system: bool = False
    ) -> Dict[str, Any]:
        """运行智能体

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

        Returns:
            执行结果
        """
        # 初始化状态
        initial_state: SlidesAgentState = {
            "result_id": result_id,
            "paper_id": paper_id,
            "source": source,
            "paper_type": paper_type,
            "agent_type": agent_type,
            "user_id": user_id,
            "style": style,
            "language": language,
            "density": density,
            "update_system": update_system,
            "local_md_path": None,
            "output_folder": None,
            "output_files": None,
            "file_path": None,
            "images": None,
            "current_step": "init",
            "status": "pending",
            "error_message": None
        }

        try:
            # 执行工作流
            final_state = await self.app.ainvoke(initial_state)

            return {
                "result_id": final_state.get("result_id"),
                "status": final_state.get("status") or "failed",
                "file_path": final_state.get("file_path"),
                "images": final_state.get("images"),
                "error_message": final_state.get("error_message")
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"智能体执行失败: {error_msg}\n{traceback.format_exc()}")
            return {
                "result_id": result_id,
                "status": "failed",
                "file_path": None,
                "images": None,
                "error_message": error_msg
            }


# ==================== 便捷函数 ====================

async def run_slides_agent(
    result_id: str,
    paper_id: str,
    source: str,
    paper_type: str,
    agent_type: str,
    user_id: str,
    style: str = "doraemon",
    language: str = "ZH",
    density: str = "medium"
) -> Dict[str, Any]:
    """运行演示文稿生成智能体

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

    Returns:
        执行结果
    """
    agent = SlidesAgent()
    return await agent.run(
        result_id=result_id,
        paper_id=paper_id,
        source=source,
        paper_type=paper_type,
        agent_type=agent_type,
        user_id=user_id,
        style=style,
        language=language,
        density=density
    )
