"""
视频解析器
- 提取关键帧并OCR识别画面文字
- 提取音频并转文字（如果有whisper）
"""
from typing import List, Dict
import os
import tempfile


def parse_video(file_path: str) -> List[Dict]:
    """解析视频，提取画面文字和音频文字"""
    results = []
    
    # 提取关键帧并OCR
    frame_texts = _extract_frame_text(file_path)
    if frame_texts:
        results.append({
            "file_name": os.path.basename(file_path),
            "text": "\n".join(frame_texts),
            "source": "video_ocr",
        })
    
    # 提取音频并转文字
    audio_text = _extract_audio_text(file_path)
    if audio_text:
        results.append({
            "file_name": os.path.basename(file_path) + "_audio",
            "text": audio_text,
            "source": "video_audio",
        })
    
    return results


def _extract_frame_text(file_path: str) -> List[str]:
    """提取视频关键帧并OCR"""
    texts = []
    
    try:
        import cv2
        from PIL import Image
        import pytesseract
        
        try:
            pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        except Exception:
            pass
        
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            return texts
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # 每5秒提取一帧
        frame_interval = int(fps * 5)
        frame_idx = 0
        
        while frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            
            # 转为PIL Image
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            # OCR
            text = pytesseract.image_to_string(pil_img, lang="chi_sim+eng")
            text = text.strip()
            if text and len(text) > 3:
                texts.append(f"[{_format_time(frame_idx / fps)}] {text}")
            
            frame_idx += frame_interval
        
        cap.release()
    except Exception:
        pass
    
    return texts


def _extract_audio_text(file_path: str) -> str:
    """提取音频并转文字（使用whisper）"""
    try:
        import whisper
        
        model = whisper.load_model("base")
        result = model.transcribe(file_path, language="zh")
        return result.get("text", "")
    except Exception:
        return ""


def _format_time(seconds: float) -> str:
    """格式化时间"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
