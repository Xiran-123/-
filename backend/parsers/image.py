"""
图片解析器（OCR文字识别）
支持 jpg, jpeg, png, bmp, gif
"""
from typing import List, Dict
import os


def parse_image(file_path: str) -> List[Dict]:
    """解析图片，提取文字"""
    results = []
    
    # 优先使用pytesseract + tesseract
    text = _ocr_with_tesseract(file_path)
    
    if not text or len(text.strip()) < 5:
        # 降级：尝试使用easyocr
        text = _ocr_with_easyocr(file_path)
    
    if text and text.strip():
        results.append({
            "file_name": os.path.basename(file_path),
            "text": text.strip(),
            "source": "image_ocr",
        })
    
    return results


def _ocr_with_tesseract(file_path: str) -> str:
    """使用tesseract进行OCR"""
    try:
        import pytesseract
        from PIL import Image
        
        # 尝试配置tesseract路径（Windows常见路径）
        try:
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        except Exception:
            pass
        
        img = Image.open(file_path)
        # 中英文识别
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return text
    except Exception:
        return ""


def _ocr_with_easyocr(file_path: str) -> str:
    """使用easyocr进行OCR"""
    try:
        import easyocr
        import numpy as np
        from PIL import Image
        
        reader = easyocr.Reader(["ch_sim", "en"], verbose=False)
        img = Image.open(file_path)
        img_array = np.array(img)
        result = reader.readtext(img_array)
        text = "\n".join([item[1] for item in result])
        return text
    except Exception:
        return ""
