"""
纯文本解析器
支持 .txt, .csv, .json, .md 等文本文件
"""
import os
import json
import csv
from typing import List, Dict


def parse_text(file_path: str) -> List[Dict]:
    """解析纯文本文件"""
    ext = file_path.rsplit(".", 1)[-1].lower()
    results = []
    
    if ext == "csv":
        results = _parse_csv(file_path)
    elif ext == "json":
        results = _parse_json(file_path)
    else:
        results = _parse_plain_text(file_path)
    
    return results


def _detect_encoding(file_path: str) -> str:
    try:
        import chardet
        with open(file_path, "rb") as f:
            raw = f.read(10000)
        result = chardet.detect(raw)
        return result.get("encoding", "utf-8") or "utf-8"
    except Exception:
        return "utf-8"


def _parse_plain_text(file_path: str) -> List[Dict]:
    """解析纯文本"""
    encoding = _detect_encoding(file_path)
    
    try:
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            content = f.read()
    except Exception:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    
    results = []
    if content.strip():
        results.append({
            "file_name": os.path.basename(file_path),
            "text": content,
            "source": "text",
        })
    
    return results


def _parse_csv(file_path: str) -> List[Dict]:
    """解析CSV文件"""
    encoding = _detect_encoding(file_path)
    results = []
    
    try:
        with open(file_path, "r", encoding=encoding, errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = " ".join([f"{k}: {v}" for k, v in row.items() if v])
                if text:
                    results.append({
                        "file_name": os.path.basename(file_path),
                        "text": text,
                        "source": "csv",
                    })
    except Exception:
        results = _parse_plain_text(file_path)
    
    return results


def _parse_json(file_path: str) -> List[Dict]:
    """解析JSON文件"""
    encoding = _detect_encoding(file_path)
    results = []
    
    try:
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            data = json.load(f)
        
        text = json.dumps(data, ensure_ascii=False, indent=2)
        results.append({
            "file_name": os.path.basename(file_path),
            "text": text,
            "source": "json",
        })
    except Exception:
        results = _parse_plain_text(file_path)
    
    return results
