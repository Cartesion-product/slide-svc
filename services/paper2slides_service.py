"""Paper2Slides服务封装模块

封装Paper2Slides核心功能，提供统一的服务接口。
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from config.settings import get_settings
from common.enums import OutputTypeEnum, StyleTypeEnum, ContentTypeEnum
from common.constants import (
    OUTPUT_DIR,
    UPLOAD_DIR,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_OUTPUT_TYPE,
    DEFAULT_STYLE,
    DEFAULT_SLIDES_LENGTH,
    DEFAULT_POSTER_DENSITY,
    DEFAULT_FAST_MODE
)

# Paper2Slides核心模块导入
from paper2slides.core import (
    run_pipeline,
    list_outputs,
    get_base_dir,
    get_config_dir,
    get_config_name,
    detect_start_stage,
    load_state
)
from paper2slides.utils.path_utils import get_project_name

logger = logging.getLogger(__name__)


class Paper2SlidesService:
    """Paper2Slides服务封装类

    提供演示文稿和全景信息图生成的统一服务接口。
    """

    def __init__(self):
        self.settings = get_settings()
        self._base_path = Path(__file__).parent.parent

        # 输出目录
        self.output_dir = self._base_path / OUTPUT_DIR
        # 上传目录
        self.upload_dir = self._base_path / UPLOAD_DIR

        # 确保目录存在
        self.output_dir.mkdir(exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def build_config(
        self,
        input_path: str,
        content_type: str = DEFAULT_CONTENT_TYPE,
        output_type: str = DEFAULT_OUTPUT_TYPE,
        style: str = DEFAULT_STYLE,
        custom_style: Optional[str] = None,
        length: str = DEFAULT_SLIDES_LENGTH,
        density: str = DEFAULT_POSTER_DENSITY,
        fast_mode: bool = DEFAULT_FAST_MODE
    ) -> Dict[str, Any]:
        """构建Pipeline配置

        Args:
            input_path: 输入文件路径
            content_type: 内容类型 (paper/general)
            output_type: 输出类型 (slides/poster)
            style: 风格类型 (academic/doraemon/custom)
            custom_style: 自定义风格描述
            length: slides长度 (short/medium/long)
            density: poster密度 (sparse/medium/dense)
            fast_mode: 是否启用快速模式

        Returns:
            Pipeline配置字典
        """
        return {
            "input_path": input_path,
            "content_type": content_type,
            "output_type": output_type,
            "style": style,
            "custom_style": custom_style,
            "slides_length": length,
            "poster_density": density,
            "fast_mode": fast_mode if content_type == ContentTypeEnum.PAPER.value else False,
        }

    def get_project_dirs(
        self,
        file_paths: List[str],
        session_id: str,
        config: Dict[str, Any]
    ) -> tuple:
        """获取项目目录

        Args:
            file_paths: 输入文件路径列表
            session_id: 会话ID
            config: Pipeline配置

        Returns:
            (base_dir, config_dir) 元组
        """
        # 获取项目名称
        if len(file_paths) > 1:
            project_name = f"session_{session_id[:8]}"
        else:
            project_name = get_project_name(file_paths[0])

        # 获取目录
        base_dir = get_base_dir(str(self.output_dir), project_name, config["content_type"])
        config_dir = get_config_dir(base_dir, config)

        return base_dir, config_dir

    def detect_start_stage(
        self,
        base_dir: Path,
        config_dir: Path,
        config: Dict[str, Any]
    ) -> str:
        """检测起始阶段

        根据已存在的检查点文件，确定从哪个阶段开始执行。

        Args:
            base_dir: 基础目录
            config_dir: 配置目录
            config: Pipeline配置

        Returns:
            起始阶段名称
        """
        return detect_start_stage(base_dir, config_dir, config)

    async def generate(
        self,
        session_id: str,
        file_paths: List[str],
        config: Dict[str, Any],
        session_manager=None
    ) -> Dict[str, Any]:
        """执行生成任务

        Args:
            session_id: 会话ID
            file_paths: 输入文件路径列表
            config: Pipeline配置
            session_manager: 会话管理器（用于取消检测）

        Returns:
            生成结果字典，包含输出目录和文件列表
        """
        # 获取项目目录
        base_dir, config_dir = self.get_project_dirs(file_paths, session_id, config)

        # 检测起始阶段
        from_stage = self.detect_start_stage(base_dir, config_dir, config)

        logger.info(f"Starting pipeline from stage: {from_stage}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Base dir: {base_dir}")
        logger.info(f"Config dir: {config_dir}")

        # 运行Pipeline
        await run_pipeline(
            base_dir,
            config_dir,
            config,
            from_stage,
            session_id,
            session_manager
        )

        # 收集输出文件
        output_files = self._collect_output_files(config_dir)

        return {
            "output_dir": str(config_dir),
            "output_files": output_files,
            "num_files": len(output_files)
        }

    def get_task_status(self, config_dir: Path) -> Optional[Dict[str, Any]]:
        """获取任务状态

        Args:
            config_dir: 配置目录

        Returns:
            任务状态字典，如果不存在则返回None
        """
        return load_state(config_dir)

    def list_all_outputs(self) -> None:
        """列出所有输出

        打印所有项目及其输出配置。
        """
        list_outputs(str(self.output_dir))

    def _collect_output_files(self, config_dir: Path) -> List[Dict[str, str]]:
        """收集输出文件

        Args:
            config_dir: 配置目录

        Returns:
            输出文件列表，每项包含filename, path, relative_path
        """
        output_files = []
        if config_dir.exists():
            # 查找最新的时间戳目录
            timestamp_dirs = sorted(
                [d for d in config_dir.iterdir() if d.is_dir()],
                reverse=True
            )
            if timestamp_dirs:
                latest_output = timestamp_dirs[0]
                for file_path in latest_output.iterdir():
                    if file_path.is_file():
                        output_files.append({
                            "filename": file_path.name,
                            "path": str(file_path),
                            "relative_path": str(file_path.relative_to(self.output_dir))
                        })
        return output_files

    def get_output_images(self, config_dir: Path) -> List[str]:
        """获取输出图片列表（用于slides）

        Args:
            config_dir: 配置目录

        Returns:
            图片文件路径列表
        """
        images = []
        if config_dir.exists():
            timestamp_dirs = sorted(
                [d for d in config_dir.iterdir() if d.is_dir()],
                reverse=True
            )
            if timestamp_dirs:
                latest_output = timestamp_dirs[0]
                for file_path in latest_output.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
                        images.append(str(file_path))
        return sorted(images)


# 服务单例
_service_instance: Optional[Paper2SlidesService] = None


def get_paper2slides_service() -> Paper2SlidesService:
    """获取Paper2Slides服务单例

    Returns:
        Paper2SlidesService实例
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = Paper2SlidesService()
    return _service_instance
