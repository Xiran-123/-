"""
微信聊天记录解析器
支持格式：
- .txt (微信PC端导出，格式：[时间] 发送人: 内容)
- .csv
- .html (微信导出的HTML聊天记录)
- .json
"""
import re
import json
import csv
from html.parser import HTMLParser
from datetime import datetime
from typing import List, Dict, Optional


class WechatMessage:
    """微信消息"""
    def __init__(self, time: str, sender: str, content: str, msg_type: str = "text"):
        self.time = time
        self.sender = sender
        self.content = content
        self.msg_type = msg_type

    def to_dict(self):
        return {
            "time": self.time,
            "sender": self.sender,
            "content": self.content,
            "msg_type": self.msg_type,
        }


def _detect_encoding(file_path: str) -> str:
    """检测文件编码"""
    try:
        import chardet
        with open(file_path, "rb") as f:
            raw = f.read(10000)
        result = chardet.detect(raw)
        return result.get("encoding", "utf-8") or "utf-8"
    except Exception:
        return "utf-8"


def parse_wechat(file_path: str) -> List[WechatMessage]:
    """解析微信聊天记录"""
    ext = file_path.rsplit(".", 1)[-1].lower()
    
    if ext in ("txt",):
        return _parse_txt(file_path)
    elif ext == "csv":
        return _parse_csv(file_path)
    elif ext in ("html", "htm"):
        return _parse_html(file_path)
    elif ext == "json":
        return _parse_json(file_path)
    else:
        # 尝试按文本解析
        return _parse_txt(file_path)


def _parse_txt(file_path: str) -> List[WechatMessage]:
    """解析txt格式微信聊天记录"""
    encoding = _detect_encoding(file_path)
    messages = []
    
    # 常见格式: [2024-01-01 12:00:00] 张三: 你好
    # 或者: 2024-01-01 12:00:00 张三 你好
    # 或者: 张三 (2024-01-01 12:00:00): 你好
    patterns = [
        re.compile(r'^\[?(\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]\d{1,2}:\d{2}(?::\d{2})?)\]?\s*([^:：]+)[:：]\s*(.*)$'),
        re.compile(r'^([^:：()]+)\s*[（(](\d{4}[-/]\d{1,2}[-/]\d{1,2}[\sT]?\d{0,2}:?\d{0,2}:?\d{0,2})[)）]\s*[:：]\s*(.*)$'),
    ]
    
    try:
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            lines = f.readlines()
    except Exception:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    
    current_time = ""
    current_sender = ""
    
    for line in lines:
        line = line.rstrip("\n").rstrip("\r")
        if not line.strip():
            continue
        
        matched = False
        for pattern in patterns:
            m = pattern.match(line)
            if m:
                groups = m.groups()
                if len(groups) == 3:
                    # 判断时间位置
                    if groups[0].startswith("20") or groups[0][:4].isdigit():
                        time_str, sender, content = groups
                    else:
                        sender, time_str, content = groups
                    current_time = time_str
                    current_sender = sender.strip()
                    content = content.strip()
                    if content:
                        messages.append(WechatMessage(current_time, current_sender, content))
                    matched = True
                    break
        
        if not matched and current_sender:
            # 可能是上一条消息的续行
            if line.strip():
                if messages:
                    messages[-1].content += "\n" + line.strip()
    
    return messages


def _parse_csv(file_path: str) -> List[WechatMessage]:
    """解析csv格式"""
    encoding = _detect_encoding(file_path)
    messages = []
    
    try:
        with open(file_path, "r", encoding=encoding, errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                time = row.get("时间") or row.get("time") or row.get("Time") or ""
                sender = row.get("发送人") or row.get("sender") or row.get("Sender") or row.get("昵称") or ""
                content = row.get("内容") or row.get("content") or row.get("消息") or row.get("message") or ""
                if content:
                    messages.append(WechatMessage(str(time), str(sender), str(content)))
    except Exception:
        # 尝试普通CSV
        with open(file_path, "r", encoding=encoding, errors="ignore", newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    messages.append(WechatMessage(row[0], row[1], row[2]))
    
    return messages


def _parse_html(file_path: str) -> List[WechatMessage]:
    """解析微信导出的HTML聊天记录"""
    encoding = _detect_encoding(file_path)
    
    try:
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            content = f.read()
    except Exception:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    
    messages = []
    
    # 微信HTML通常用class区分消息
    # 尝试提取时间、发送人、内容
    msg_patterns = [
        # 标准微信HTML格式
        re.compile(
            r'<div[^>]*class="[^"]*message[^"]*"[^>]*>(.*?)</div>',
            re.DOTALL
        ),
    ]
    
    # 提取所有文本，按时间分割
    time_pattern = re.compile(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?\s*\d{0,2}:?\d{0,2}:?\d{0,2})')
    sender_pattern = re.compile(r'<span[^>]*class="[^"]*(?:sender|name|nickname)[^"]*"[^>]*>([^<]+)</span>', re.IGNORECASE)
    content_pattern = re.compile(r'<div[^>]*class="[^"]*(?:content|text|message-text)[^"]*"[^>]*>(.*?)</div>', re.DOTALL | re.IGNORECASE)
    
    # 简单的HTML转文本
    class HTMLTextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = []
            self.skip = False
        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style"):
                self.skip = True
        def handle_endtag(self, tag):
            if tag in ("script", "style"):
                self.skip = False
        def handle_data(self, data):
            if not self.skip:
                self.text.append(data)
    
    extractor = HTMLTextExtractor()
    extractor.feed(content)
    text = "\n".join(extractor.text)
    
    # 按时间分割消息
    parts = time_pattern.split(text)
    for i in range(1, len(parts), 2):
        time_str = parts[i]
        rest = parts[i + 1] if i + 1 < len(parts) else ""
        # 发送人和内容
        rest = rest.strip()
        if rest:
            # 尝试分割发送人和内容
            colon_idx = rest.find(":")
            if colon_idx == -1:
                colon_idx = rest.find("：")
            if colon_idx > 0 and colon_idx < 50:
                sender = rest[:colon_idx].strip()
                msg_content = rest[colon_idx + 1:].strip()
            else:
                sender = ""
                msg_content = rest
            if msg_content:
                messages.append(WechatMessage(time_str, sender, msg_content))
    
    return messages


def _parse_json(file_path: str) -> List[WechatMessage]:
    """解析json格式"""
    encoding = _detect_encoding(file_path)
    messages = []
    
    try:
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    time = item.get("时间") or item.get("time") or item.get("Time") or ""
                    sender = item.get("发送人") or item.get("sender") or item.get("Sender") or item.get("昵称") or ""
                    content = item.get("内容") or item.get("content") or item.get("消息") or item.get("message") or item.get("text") or ""
                    if content:
                        messages.append(WechatMessage(str(time), str(sender), str(content)))
        elif isinstance(data, dict):
            # 可能是 {"messages": [...]} 格式
            msg_list = data.get("messages") or data.get("聊天记录") or []
            for item in msg_list:
                if isinstance(item, dict):
                    time = item.get("时间") or item.get("time") or ""
                    sender = item.get("发送人") or item.get("sender") or ""
                    content = item.get("内容") or item.get("content") or item.get("text") or ""
                    if content:
                        messages.append(WechatMessage(str(time), str(sender), str(content)))
    except Exception:
        pass
    
    return messages
