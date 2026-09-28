"""
幻象机 - 人设知识库系统 API
"""
import os
import sys
import uuid
import json
import time
import traceback
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# 添加backend到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from parsers import parse_wechat, parse_word, parse_image, parse_text, parse_video
from persona import PersonaExtractor, PersonaProfile
from knowledge import VectorStore

app = FastAPI(title="幻象机 - 人设知识库系统", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
vector_store = VectorStore(config.KNOWLEDGE_DIR, config.VECTOR_MODEL)
persona_store: dict = {}  # persona_id -> PersonaProfile

# 加载已有人设
def load_personas():
    if not os.path.exists(config.PERSONA_DIR):
        return
    for f in os.listdir(config.PERSONA_DIR):
        if f.endswith(".json"):
            pid = f[:-5]
            try:
                profile = PersonaExtractor.load(pid, config.PERSONA_DIR)
                if profile:
                    persona_store[pid] = profile
            except Exception:
                pass

load_personas()


# ============ 请求模型 ============

class ExtractPersonaRequest(BaseModel):
    files: List[str]  # 已上传的文件名
    persona_name: str = "默认人设"
    target_sender: str = ""  # 指定要提取的发送人（微信聊天记录中）


class ChatRequest(BaseModel):
    persona_id: str
    message: str
    use_knowledge: bool = True
    top_k: int = 5


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


# ============ 前端页面 ============

@app.get("/")
async def index():
    """前端页面"""
    frontend_path = os.path.join(os.path.dirname(config.BASE_DIR), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "幻象机人设知识库系统 API 运行中，请访问 /docs 查看接口文档"}


# ============ 文件上传与解析 ============

@app.post("/api/upload")
async def upload_file(files: List[UploadFile] = File(...)):
    """上传文件并解析"""
    results = []
    
    for file in files:
        try:
            # 检查扩展名
            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext and ext not in config.ALLOWED_EXTENSIONS:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": f"不支持的文件格式: {ext}",
                })
                continue
            
            # 保存文件
            file_id = str(uuid.uuid4())
            save_name = f"{file_id}_{file.filename}"
            save_path = os.path.join(config.UPLOAD_DIR, save_name)
            
            content = await file.read()
            if len(content) > config.MAX_FILE_SIZE:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": f"文件过大，最大支持 {config.MAX_FILE_SIZE // 1024 // 1024}MB",
                })
                continue
            
            with open(save_path, "wb") as f:
                f.write(content)
            
            # 解析文件
            parsed = await parse_file(save_path, ext, file.filename)
            parsed["file_id"] = file_id
            parsed["filename"] = file.filename
            results.append(parsed)
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e),
            })
    
    return {"results": results}


async def parse_file(file_path: str, ext: str, original_name: str) -> dict:
    """解析单个文件"""
    try:
        if ext in ("txt", "csv", "json", "html", "htm"):
            # 尝试微信解析，失败则文本解析
            messages = parse_wechat(file_path)
            if messages and len(messages) > 1:
                # 转为知识库文本
                contents = [f"[{m.time}] {m.sender}: {m.content}" for m in messages]
                # 添加到知识库
                chunk_ids = vector_store.add_documents(
                    source_type="wechat",
                    source_name=original_name,
                    contents=contents,
                )
                return {
                    "success": True,
                    "type": "wechat",
                    "message_count": len(messages),
                    "senders": list(set(m.sender for m in messages)),
                    "chunk_count": len(chunk_ids),
                    "preview": "\n".join(contents[:5]),
                }
            else:
                # 按文本处理
                docs = parse_text(file_path)
                contents = [d["text"] for d in docs]
                chunk_ids = vector_store.add_documents(
                    source_type="text",
                    source_name=original_name,
                    contents=contents,
                )
                return {
                    "success": True,
                    "type": "text",
                    "chunk_count": len(chunk_ids),
                    "preview": contents[0][:200] if contents else "",
                }
        
        elif ext in ("docx", "doc"):
            paragraphs = parse_word(file_path)
            contents = [p["content"] for p in paragraphs]
            chunk_ids = vector_store.add_documents(
                source_type="word",
                source_name=original_name,
                contents=contents,
            )
            return {
                "success": True,
                "type": "word",
                "paragraph_count": len(paragraphs),
                "chunk_count": len(chunk_ids),
                "preview": "\n".join(contents[:3])[:200],
            }
        
        elif ext in ("jpg", "jpeg", "png", "bmp", "gif"):
            results = parse_image(file_path)
            contents = [r["text"] for r in results]
            chunk_ids = vector_store.add_documents(
                source_type="image",
                source_name=original_name,
                contents=contents,
            )
            return {
                "success": True,
                "type": "image",
                "chunk_count": len(chunk_ids),
                "text_preview": contents[0][:200] if contents else "（未识别到文字）",
            }
        
        elif ext in ("mp4", "avi", "mov", "mkv", "flv"):
            results = parse_video(file_path)
            contents = [r["text"] for r in results]
            chunk_ids = vector_store.add_documents(
                source_type="video",
                source_name=original_name,
                contents=contents,
            )
            return {
                "success": True,
                "type": "video",
                "chunk_count": len(chunk_ids),
                "preview": contents[0][:200] if contents else "",
            }
        
        else:
            return {
                "success": False,
                "error": f"未处理的文件类型: {ext}",
            }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"解析失败: {str(e)}",
            "traceback": traceback.format_exc()[:500],
        }


# ============ 人设提取 ============

@app.post("/api/persona/extract")
async def extract_persona(req: ExtractPersonaRequest):
    """提取人设"""
    try:
        # 收集所有已上传文件的内容
        all_messages = []
        all_documents = []
        
        for file_id_or_name in req.files:
            # 查找上传的文件
            matched_files = [
                f for f in os.listdir(config.UPLOAD_DIR)
                if file_id_or_name in f or f.endswith(file_id_or_name)
            ]
            
            for fname in matched_files:
                fpath = os.path.join(config.UPLOAD_DIR, fname)
                ext = fname.rsplit(".", 1)[-1].lower()
                
                if ext in ("txt", "csv", "json", "html", "htm"):
                    messages = parse_wechat(fpath)
                    if messages:
                        # 如果指定了发送人，过滤
                        if req.target_sender:
                            messages = [m for m in messages if m.sender == req.target_sender]
                        all_messages.extend([m.to_dict() for m in messages])
                elif ext in ("docx", "doc"):
                    paragraphs = parse_word(fpath)
                    all_documents.extend([{
                        "file_name": fname,
                        "text": p["content"],
                        "source": "word",
                    } for p in paragraphs])
                else:
                    docs = parse_text(fpath)
                    all_documents.extend(docs)
        
        # 提取人设
        extractor = PersonaExtractor()
        if all_messages:
            profile = extractor.extract_from_messages(all_messages)
        elif all_documents:
            profile = extractor.extract_from_documents(all_documents)
        else:
            raise HTTPException(status_code=400, detail="未找到可分析的内容")
        
        # 保存人设
        persona_id = str(uuid.uuid4())[:8]
        extractor.save(persona_id, config.PERSONA_DIR)
        persona_store[persona_id] = profile
        
        return {
            "success": True,
            "persona_id": persona_id,
            "persona": profile.to_dict(),
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"人设提取失败: {str(e)}")


@app.get("/api/persona/list")
async def list_personas():
    """列出所有人设"""
    personas = []
    for pid, profile in persona_store.items():
        personas.append({
            "persona_id": pid,
            "name": profile.name or "未命名",
            "traits": profile.personality_traits,
            "total_messages": profile.total_messages,
            "created_at": os.path.getmtime(
                os.path.join(config.PERSONA_DIR, f"{pid}.json")
            ) if os.path.exists(os.path.join(config.PERSONA_DIR, f"{pid}.json")) else None,
        })
    return {"personas": personas}


@app.get("/api/persona/{persona_id}")
async def get_persona(persona_id: str):
    """获取指定人设详情"""
    profile = persona_store.get(persona_id)
    if not profile:
        # 尝试从文件加载
        profile = PersonaExtractor.load(persona_id, config.PERSONA_DIR)
        if profile:
            persona_store[persona_id] = profile
    if not profile:
        raise HTTPException(status_code=404, detail="人设不存在")
    return {"persona": profile.to_dict()}


@app.delete("/api/persona/{persona_id}")
async def delete_persona(persona_id: str):
    """删除人设"""
    if persona_id in persona_store:
        del persona_store[persona_id]
    file_path = os.path.join(config.PERSONA_DIR, f"{persona_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
    return {"success": True}


# ============ 知识库管理 ============

@app.get("/api/knowledge/stats")
async def knowledge_stats():
    """获取知识库统计"""
    return vector_store.get_stats()


@app.post("/api/knowledge/search")
async def knowledge_search(req: SearchRequest):
    """检索知识库"""
    results = vector_store.search(req.query, top_k=req.top_k)
    return {
        "results": [
            {
                "content": chunk.content,
                "source_type": chunk.source_type,
                "source_name": chunk.source_name,
                "score": score,
            }
            for chunk, score in results
        ]
    }


@app.delete("/api/knowledge")
async def clear_knowledge():
    """清空知识库"""
    vector_store.clear()
    return {"success": True}


# ============ 对话测试 ============

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """与人设对话（基于知识库 + 人设prompt）"""
    profile = persona_store.get(req.persona_id)
    if not profile:
        profile = PersonaExtractor.load(req.persona_id, config.PERSONA_DIR)
    if not profile:
        raise HTTPException(status_code=404, detail="人设不存在")
    
    # 检索相关知识
    context = ""
    if req.use_knowledge:
        results = vector_store.search(req.message, top_k=req.top_k)
        if results:
            context_parts = []
            for chunk, score in results:
                if score > 0.3:  # 相似度阈值
                    context_parts.append(f"[相关记忆|{chunk.source_name}] {chunk.content}")
            context = "\n".join(context_parts)
    
    return {
        "persona_id": req.persona_id,
        "persona_name": profile.name,
        "system_prompt": profile.system_prompt,
        "user_message": req.message,
        "retrieved_context": context,
        "instruction": "请将 system_prompt 作为系统提示词，retrieved_context 作为参考上下文，"
                       "结合 user_message 生成回复。可接入任意LLM API。",
    }


# ============ 幻象机接入API ============

@app.get("/api/phantom/persona/{persona_id}")
async def phantom_get_persona(persona_id: str):
    """
    幻象机接入：获取人设prompt
    幻象机调用此接口获取完整的人设系统提示词
    """
    profile = persona_store.get(persona_id)
    if not profile:
        profile = PersonaExtractor.load(persona_id, config.PERSONA_DIR)
    if not profile:
        raise HTTPException(status_code=404, detail="人设不存在")
    
    return {
        "persona_id": persona_id,
        "name": profile.name,
        "system_prompt": profile.system_prompt,
        "persona_data": profile.to_dict(),
    }


@app.post("/api/phantom/context/{persona_id}")
async def phantom_get_context(persona_id: str, req: SearchRequest):
    """
    幻象机接入：获取对话相关的记忆上下文（RAG）
    幻象机在生成回复前调用此接口，获取与用户消息相关的历史记忆
    """
    results = vector_store.search(req.query, top_k=req.top_k)
    
    return {
        "persona_id": persona_id,
        "query": req.query,
        "context": [
            {
                "content": chunk.content,
                "source": chunk.source_name,
                "relevance": score,
            }
            for chunk, score in results
        ],
    }


@app.get("/api/phantom/list")
async def phantom_list_personas():
    """
    幻象机接入：列出所有可用人设
    """
    personas = []
    for pid, profile in persona_store.items():
        personas.append({
            "persona_id": pid,
            "name": profile.name or "未命名",
            "traits": profile.personality_traits,
            "total_messages": profile.total_messages,
        })
    return {"personas": personas}


@app.get("/api/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "knowledge": vector_store.get_stats(),
        "persona_count": len(persona_store),
    }


# 挂载静态文件
frontend_dir = os.path.join(os.path.dirname(config.BASE_DIR), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    print(f"幻象机人设知识库系统启动中... http://{config.HOST}:{config.PORT}")
    uvicorn.run(app, host=config.HOST, port=config.PORT)
