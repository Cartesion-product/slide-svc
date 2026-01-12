"""常量定义模块"""
import os

# ============ 应用配置 ============

# 应用配置文件名称
APPLICATION_CONFIG_FILE_NAME = "appconfig.json"

# ============ 服务信息 ============

# 服务名称
SERVICE_NAME = "slide-svc"

# 服务标题
SERVICE_TITLE = "演示文稿Agent服务"

# 服务描述
SERVICE_DESCRIPTION = "基于LangGraph的智能演示文稿生成服务"

# 服务版本
SERVICE_VERSION = "1.0.0"

# ============ API配置 ============

# API版本
API_VERSION = "v1"

# API前缀
API_PREFIX = f"/api/{API_VERSION}"

# ============ 任务配置 ============

# 任务标题模板
TASK_TITLE_POSTER = "全景信息图"
TASK_TITLE_SLIDES = "演示文稿"

# 任务队列限制
MAX_RUNNING_TASKS = 3
MAX_WAITING_TASKS = 5

# 默认超时时间（秒）
DEFAULT_TASK_TIMEOUT = 600

# ============ 文件配置 ============

# 文件存储路径
UPLOAD_DIR = "sources/uploads"
OUTPUT_DIR = "outputs"

# 支持的文件类型
SUPPORTED_FILE_TYPES = {".pdf", ".md"}

# 预定义风格
PREDEFINED_STYLES = {"academic", "doraemon"}

# ============ MinIO配置键 ============

MINIO_ENDPOINT_KEY = "KB_MINIO_ENDPOINT"
MINIO_ACCESS_KEY = "KB_MINIO_ACCESSKEY"
MINIO_SECRET_KEY = "KB_MINIO_SECRETKEY"
MINIO_BUCKET_KEY = "KB_MINIO_BUCKET"

# ============ Paper2Slides配置 ============

# 默认内容类型
DEFAULT_CONTENT_TYPE = "paper"

# 默认输出类型
DEFAULT_OUTPUT_TYPE = "slides"

# 默认风格
DEFAULT_STYLE = "doraemon"

# 默认长度（slides）
DEFAULT_SLIDES_LENGTH = "medium"

# 默认密度（poster）
DEFAULT_POSTER_DENSITY = "medium"

# 默认快速模式
DEFAULT_FAST_MODE = True
