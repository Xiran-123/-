"""
幻象机 - 人设知识库系统 配置
"""
import os

# HuggingFace 国内镜像（解决模型下载超时问题）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# 数据目录
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
KNOWLEDGE_DIR = os.path.join(DATA_DIR, "knowledge")
PERSONA_DIR = os.path.join(DATA_DIR, "persona")

# 确保目录存在
for d in [DATA_DIR, UPLOAD_DIR, KNOWLEDGE_DIR, PERSONA_DIR]:
    os.makedirs(d, exist_ok=True)

# 向量模型配置
VECTOR_MODEL = os.getenv("VECTOR_MODEL", "shibing624/text2vec-base-chinese")

# LLM配置（可选，用于增强人设提取）
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

# 服务配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# 文件解析配置
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB
ALLOWED_EXTENSIONS = {
    "txt", "csv", "html", "htm", "json",  # 文本类
    "docx", "doc",  # Word
    "jpg", "jpeg", "png", "bmp", "gif",  # 图片
    "mp4", "avi", "mov", "mkv", "flv",  # 视频
}

# 人设提取配置
PERSONA_SAMPLE_SIZE = 200  # 提取人设时采样的消息数量
CHUNK_SIZE = 500  # 知识库分块大小
CHUNK_OVERLAP = 50  # 分块重叠
