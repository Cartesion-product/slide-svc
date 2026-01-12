"""演示文稿 Agent API 路由模块

基于接口设计文档实现 REST API 接口。
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from middleware.auth import token_decoder
from services.task_service import get_task_service, TaskService
from common.enums import AgentTypeEnum, TaskStatusEnum, PaperTypeEnum
from common.constants import SERVICE_NAME, SERVICE_VERSION
from exception.exceptions import TaskQueueFullException, TaskNotFoundException, InvalidRequestException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["演示文稿Agent"])


# ============ 请求/响应模型 ============

class TaskCreateRequest(BaseModel):
    """任务创建请求"""
    paper_id: str = Field(..., description="论文ID")
    title: Optional[str] = Field(None, description="任务标题")
    source: str = Field(..., description="论文数据源 (arxiv/acl/neurips)")
    source_path: str = Field(..., description="MinIO文件路径（包括桶名）")
    paper_type: str = Field("system", description="论文类型 (system/user)")
    agent_type: str = Field(..., description="任务类型 (poster/slides)")
    bucket: str = Field("kb-paper-parsed", description="论文解析结果桶名")
    style: Optional[str] = Field(None, description="风格偏好")
    language: str = Field("ZH", description="语言 (ZH/EN)")
    density: str = Field("medium", description="内容密度 (sparse/medium/dense)")


class BaseResponse(BaseModel):
    """基础响应"""
    code: int = 200
    message: str = "success"
    data: Optional[dict] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    service: str
    version: str
    timestamp: str


# ============ 依赖注入 ============

def get_service() -> TaskService:
    """获取任务服务"""
    return get_task_service()





# ============ API 接口 ============

@router.get("/health", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """服务健康检查接口"""
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        timestamp=datetime.now().isoformat()
    )


@router.post("/namespace/{namespace}/tasks/create", response_model=BaseResponse, summary="创建任务")
async def create_task(
    namespace: str = Path(..., description="命名空间"),
    request: TaskCreateRequest = ...,
    token_payload: dict[str, None] = Depends(token_decoder),
    service: TaskService = Depends(get_service)
):
    """创建 PPT/Poster 生成任务

    业务逻辑:
    1. 验证必填参数（paper_id, source, agent_type），并从token_payload获取user_id
    2. 检查任务队列（可执行任务上限2，等待队列上限5）
    3. 创建任务记录，状态为"等待中"
    4. 如果是系统论文且有默认结果，直接使用默认结果；否则提交Celery异步任务
    """
    try:
        # 从token_payload中获取user_id
        user_id = token_payload.get("user_id", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="用户未认证")

        # 验证参数
        if request.agent_type not in (AgentTypeEnum.POSTER.value, AgentTypeEnum.SLIDES.value):
            raise HTTPException(status_code=400, detail="无效的任务类型，只支持 poster 或 slides")
        if request.paper_type not in (PaperTypeEnum.SYSTEM.value, PaperTypeEnum.USER.value):
            raise HTTPException(status_code=400, detail="无效的论文类型，只支持 system 或 user")

        result = service.create_task(
            paper_id=request.paper_id,
            source=request.source,
            source_path=request.source_path,
            paper_type=request.paper_type,
            agent_type=request.agent_type,
            user_id=user_id,
            title=request.title,
            bucket=request.bucket,
            style=request.style or "doraemon",
            language=request.language,
            density=request.density
        )

        return BaseResponse(
            message="任务创建成功",
            data={"task_id": result["task_id"]}
        )

    except TaskQueueFullException as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"创建任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.delete("/namespace/{namespace}/tasks/{task_id}/delete", response_model=BaseResponse, summary="删除任务")
async def delete_task(
    namespace: str = Path(..., description="命名空间"),
    task_id: str = Path(..., description="任务ID"),
    token_payload: dict[str, None] = Depends(token_decoder),
    service: TaskService = Depends(get_service)
):
    """删除任务

    如果任务正在运行，会先停止执行。删除不会影响系统论文的默认结果。
    """
    try:
        user_id = token_payload.get("user_id", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="用户未认证")

        service.delete_task(task_id, user_id)

        return BaseResponse(message="任务删除成功")

    except TaskNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.get("/namespace/{namespace}/tasks/{task_id}/detail", response_model=BaseResponse, summary="任务详情")
async def get_task_detail(
    namespace: str = Path(..., description="命名空间"),
    task_id: str = Path(..., description="任务ID"),
    token_payload: dict[str, None] = Depends(token_decoder),
    service: TaskService = Depends(get_service)
):
    """获取任务详情

    - Poster 任务: 返回标题、文件下载地址
    - Slides 任务: 返回标题、文件下载地址、图像下载地址数组
    """
    try:
        user_id = token_payload.get("user_id", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="用户未认证")

        detail = service.get_task_detail(task_id, user_id)

        return BaseResponse(message="查询成功", data=detail)

    except TaskNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.get("/namespace/{namespace}/tasks/{task_id}/download", response_model=BaseResponse, summary="任务下载")
async def get_task_download(
    namespace: str = Path(..., description="命名空间"),
    task_id: str = Path(..., description="任务ID"),
    token_payload: dict[str, None] = Depends(token_decoder),
    service: TaskService = Depends(get_service)
):
    """获取生成任务的文件下载地址

    返回 MinIO 临时访问链接和有效期。
    """
    try:
        user_id = token_payload.get("user_id", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="用户未认证")

        download_info = service.get_task_download(task_id, user_id)

        return BaseResponse(message="获取成功", data=download_info)

    except TaskNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidRequestException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取下载链接失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取下载链接失败: {str(e)}")


@router.get("/namespace/{namespace}/tasks/page", response_model=BaseResponse, summary="任务分页列表")
async def list_tasks(
    namespace: str = Path(..., description="命名空间"),
    paper_id: str = Query(..., description="论文ID"),
    source: str = Query(..., description="论文数据源"),
    page: int = Query(1, ge=0, description="页码（0表示查询所有）"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小"),
    token_payload: dict[str, None] = Depends(token_decoder),
    service: TaskService = Depends(get_service)
):
    """分页查询任务列表

    根据用户ID和paperID分页查询任务，单条记录包含标题、类型、时间。
    """
    try:
        user_id = token_payload.get("user_id", "")
        if not user_id:
            raise HTTPException(status_code=401, detail="用户未认证")

        result = service.list_tasks(
            user_id=user_id,
            paper_id=paper_id,
            source=source,
            page=page,
            page_size=page_size
        )

        return BaseResponse(message="查询成功", data=result)

    except Exception as e:
        logger.error(f"查询任务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"查询任务列表失败: {str(e)}")


@router.get("/queue/status", response_model=BaseResponse, summary="队列状态")
async def get_queue_status(
    service: TaskService = Depends(get_service)
):
    """获取任务队列状态

    返回当前运行中和等待中的任务数量。
    """
    status = service.get_queue_status()
    return BaseResponse(data=status)
