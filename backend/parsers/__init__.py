"""文件解析模块"""
from .wechat import parse_wechat
from .word import parse_word
from .image import parse_image
from .text import parse_text
from .video import parse_video

__all__ = ["parse_wechat", "parse_word", "parse_image", "parse_text", "parse_video"]
