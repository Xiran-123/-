# 幻象机 · 人设知识库系统

将微信聊天记录、Word文档、图片、视频、文本等资料转换为知识库，自动提取人物画像（人设），帮助AI精准模仿目标人物的语言风格、性格特征和知识背景。

## ✨ 功能特性

### 📥 多格式文件解析
- **微信聊天记录**：支持 `.txt` / `.csv` / `.html` / `.json` 格式导出的聊天记录
- **Word文档**：`.docx` / `.doc`，自动提取段落和表格
- **图片**：`.jpg` / `.png` / `.bmp` / `.gif`，OCR识别画面文字
- **视频**：`.mp4` / `.avi` / `.mov` 等，提取关键帧OCR + 音频转文字
- **文本**：`.txt` / `.csv` / `.json` / `.md`

### 🎭 人设提取引擎
从资料中自动分析并提取：
- **语言风格**：正式/口语化程度、平均句长、句末语气词偏好
- **常用语/口头禅**：高频短句和句首词
- **特色词汇**：基于TF-IDF的关键词提取
- **性格特征**：幽默风趣、严谨理性、热情开朗等8种标签
- **兴趣爱好**：游戏、音乐、电影、美食、运动等10个领域
- **知识领域**：计算机、设计、金融、教育、医疗、商业
- **情绪倾向**：积极乐观 / 偏消极 / 中性平稳
- **对话习惯**：提问频率、回复模式

### 🧠 向量知识库（RAG）
- 基于 **FAISS + sentence-transformers** 的向量检索
- 自动文本分块（500字/块，50字重叠）
- 支持按相似度检索相关记忆
- 降级方案：无模型时使用TF-IDF

### 🔌 幻象机接入API
为幻象机提供标准化接口：
| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/phantom/list` | GET | 获取所有可用人设 |
| `/api/phantom/persona/{id}` | GET | 获取指定人设的完整System Prompt |
| `/api/phantom/context/{id}` | POST | 获取与用户消息相关的记忆上下文 |

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Windows / Linux / macOS

### 一键启动（Windows）

双击 `start.bat` 或在PowerShell中运行：
```powershell
.\start.ps1
```

脚本会自动：
1. 创建Python虚拟环境
2. 安装依赖
3. 启动服务

### 手动启动

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 3. 安装依赖
pip install -r backend/requirements.txt

# 4. 启动服务
python backend/app.py
```

启动后访问：
- **前端页面**：http://localhost:8000
- **API文档**：http://localhost:8000/docs

## 📖 使用流程

### 1. 上传资料
进入「资料上传」页面，拖拽或选择文件上传。系统会自动解析并加入知识库。

### 2. 提取人设
进入「人设管理」页面：
- 填写人设名称
- 指定目标发送人（微信聊天记录中要分析的对象，留空则取发言最多的人）
- 选择要分析的文件
- 点击「开始提取人设」

### 3. 查看知识库
进入「知识库」页面查看统计信息，或用关键词检索相关记忆。

### 4. 对话测试
进入「对话测试」页面，选择人设后发送消息，系统会返回构建好的System Prompt和检索到的上下文。

> 💡 当前对话测试返回的是**提示词模板**，需要接入LLM API才能生成实际回复。

## 🔌 接入幻象机

幻象机调用流程：

```
1. GET /api/phantom/list          → 获取所有人设列表
2. GET /api/phantom/persona/{id}  → 获取人设System Prompt
3. 用户发消息时:
   POST /api/phantom/context/{id}  → 获取相关记忆上下文
4. 将 System Prompt + 记忆上下文 + 用户消息 发送给LLM生成回复
```

### 调用示例

```python
import requests

BASE = "http://localhost:8000"

# 1. 获取人设列表
personas = requests.get(f"{BASE}/api/phantom/list").json()

# 2. 获取人设prompt
persona_id = personas["personas"][0]["persona_id"]
persona = requests.get(f"{BASE}/api/phantom/persona/{persona_id}").json()
system_prompt = persona["system_prompt"]

# 3. 获取记忆上下文
user_msg = "你今天怎么样？"
context = requests.post(
    f"{BASE}/api/phantom/context/{persona_id}",
    json={"query": user_msg, "top_k": 5}
).json()

# 4. 构建LLM请求
messages = [
    {"role": "system", "content": system_prompt},
]
for c in context["context"]:
    messages.append({"role": "system", "content": f"[记忆] {c['content']}"})
messages.append({"role": "user", "content": user_msg})

# 发送给你的LLM...
```

## ⚙️ 可选配置

### OCR支持（图片文字识别）
安装Tesseract OCR：
1. 下载：https://github.com/UB-Mannheim/tesseract/wiki
2. 安装时勾选中文语言包
3. 默认路径 `C:\Program Files\Tesseract-OCR\tesseract.exe`

或安装easyocr：
```bash
pip install easyocr
```

### 视频处理
```bash
pip install opencv-python
# 音频转文字（可选）
pip install openai-whisper
```

### 向量模型
默认使用 `shibing624/text2vec-base-chinese`（中文），首次运行会自动下载。也可在 `.env` 中修改：
```
VECTOR_MODEL=shibing624/text2vec-base-chinese
```

## 📁 项目结构

```
幻象机/
├── backend/
│   ├── app.py              # FastAPI主应用 + 所有API
│   ├── config.py           # 配置
│   ├── requirements.txt    # 依赖
│   ├── parsers/            # 文件解析
│   │   ├── wechat.py       # 微信聊天记录
│   │   ├── word.py         # Word文档
│   │   ├── image.py        # 图片OCR
│   │   ├── video.py        # 视频提取
│   │   └── text.py         # 纯文本
│   ├── persona/            # 人设提取
│   │   └── extractor.py    # 人设画像引擎
│   └── knowledge/          # 知识库
│       └── vector_store.py # 向量存储（FAISS）
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── data/                   # 数据目录（自动创建）
│   ├── uploads/            # 上传的文件
│   ├── knowledge/          # 向量索引
│   └── persona/            # 人设文件
├── start.bat / start.ps1   # 一键启动
└── .env.example            # 环境变量模板
```

## ⚠️ 注意事项

1. **隐私安全**：所有数据均存储在本地，不会上传到任何服务器
2. **人设提取质量**：资料越多越丰富，提取的人设越准确。建议至少提供几百条聊天记录
3. **LLM接入**：当前系统生成人设Prompt和检索上下文，实际对话生成需要接入LLM API
4. **OCR依赖**：图片和视频功能需要安装Tesseract或easyocr
