/* 幻象机 · 人设知识库 - 前端逻辑 */

const API = ""; // 同源，直接用相对路径

let uploadedFiles = []; // {file, name, size}
let parsedFiles = [];   // {filename, type, message_count, preview}

// ============ 页面切换 ============
document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
        const page = item.dataset.page;
        document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
        item.classList.add("active");
        document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
        document.getElementById(`page-${page}`).classList.add("active");
        
        // 刷新对应页面数据
        if (page === "persona") loadPersonaList();
        if (page === "knowledge") loadKnowledgeStats();
        if (page === "chat") loadChatPersonas();
        if (page === "phantom") loadPhantomPersonas();
    });
});

// ============ 文件上传 ============
const uploadArea = document.getElementById("upload-area");
const fileInput = document.getElementById("file-input");
const fileList = document.getElementById("file-list");
const btnParse = document.getElementById("btn-parse");
const btnClearFiles = document.getElementById("btn-clear-files");
const parseResult = document.getElementById("parse-result");

uploadArea.addEventListener("click", () => fileInput.click());

uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
});

uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("dragover");
});

uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    handleFiles(e.dataTransfer.files);
});

fileInput.addEventListener("change", (e) => {
    handleFiles(e.target.files);
});

function handleFiles(files) {
    for (const f of files) {
        uploadedFiles.push({
            file: f,
            name: f.name,
            size: f.size,
        });
    }
    renderFileList();
}

function renderFileList() {
    fileList.innerHTML = "";
    uploadedFiles.forEach((f, idx) => {
        const item = document.createElement("div");
        item.className = "file-item";
        item.innerHTML = `
            <div class="file-item-info">
                <span>📄</span>
                <div>
                    <div class="file-item-name">${f.name}</div>
                    <div class="file-item-size">${formatSize(f.size)}</div>
                </div>
            </div>
            <button class="btn btn-ghost" onclick="removeFile(${idx})">移除</button>
        `;
        fileList.appendChild(item);
    });
    btnParse.disabled = uploadedFiles.length === 0;
}

function removeFile(idx) {
    uploadedFiles.splice(idx, 1);
    renderFileList();
}

btnClearFiles.addEventListener("click", () => {
    uploadedFiles = [];
    renderFileList();
    parseResult.innerHTML = "";
});

btnParse.addEventListener("click", async () => {
    if (uploadedFiles.length === 0) return;
    
    btnParse.disabled = true;
    btnParse.textContent = "解析中...";
    parseResult.innerHTML = "";
    
    const formData = new FormData();
    uploadedFiles.forEach(f => formData.append("files", f.file));
    
    try {
        const res = await fetch(`${API}/api/upload`, {
            method: "POST",
            body: formData,
        });
        const data = await res.json();
        
        data.results.forEach(r => {
            const div = document.createElement("div");
            div.className = `result-item ${r.success ? "success" : "error"}`;
            let content = `<div class="result-title">${r.filename} - ${r.success ? "✓ 解析成功" : "✗ 解析失败"}</div>`;
            
            if (r.success) {
                content += `<div class="persona-info">类型: ${r.type} | 知识块: ${r.chunk_count || 0}`;
                if (r.message_count) content += ` | 消息数: ${r.message_count}`;
                content += "</div>";
                if (r.preview) {
                    content += `<div class="result-preview">${r.preview.substring(0, 300)}</div>`;
                }
                if (r.text_preview) {
                    content += `<div class="result-preview">${r.text_preview.substring(0, 300)}</div>`;
                }
                parsedFiles.push({ filename: r.filename, type: r.type });
            } else {
                content += `<div class="persona-info" style="color: var(--danger)">${r.error}</div>`;
            }
            div.innerHTML = content;
            parseResult.appendChild(div);
        });
        
        uploadedFiles = [];
        renderFileList();
        updateStats();
        
    } catch (e) {
        parseResult.innerHTML = `<div class="result-item error"><div class="result-title">请求失败</div><div>${e.message}</div></div>`;
    } finally {
        btnParse.disabled = false;
        btnParse.textContent = "开始解析并加入知识库";
    }
});

// ============ 人设提取 ============
const btnExtractPersona = document.getElementById("btn-extract-persona");
const personaList = document.getElementById("persona-list");
const fileCheckboxList = document.getElementById("file-checkbox-list");

function renderFileCheckboxes() {
    fileCheckboxList.innerHTML = "";
    if (parsedFiles.length === 0) {
        fileCheckboxList.innerHTML = '<span class="hint">请先在「资料上传」页面上传并解析文件</span>';
        return;
    }
    parsedFiles.forEach(f => {
        const item = document.createElement("label");
        item.className = "checkbox-item";
        item.innerHTML = `
            <input type="checkbox" value="${f.filename}" checked>
            <span>${f.filename} (${f.type})</span>
        `;
        fileCheckboxList.appendChild(item);
    });
}

btnExtractPersona.addEventListener("click", async () => {
    const name = document.getElementById("persona-name").value.trim() || "未命名人设";
    const sender = document.getElementById("target-sender").value.trim();
    const checkedFiles = Array.from(fileCheckboxList.querySelectorAll("input:checked")).map(i => i.value);
    
    if (checkedFiles.length === 0) {
        alert("请至少选择一个文件");
        return;
    }
    
    btnExtractPersona.disabled = true;
    btnExtractPersona.textContent = "提取中...";
    
    try {
        const res = await fetch(`${API}/api/persona/extract`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                files: checkedFiles,
                persona_name: name,
                target_sender: sender,
            }),
        });
        const data = await res.json();
        
        if (data.success) {
            alert(`人设提取成功！\n人设ID: ${data.persona_id}\n人物: ${data.persona.name || "未知"}`);
            loadPersonaList();
        } else {
            alert("提取失败: " + (data.detail || "未知错误"));
        }
    } catch (e) {
        alert("请求失败: " + e.message);
    } finally {
        btnExtractPersona.disabled = false;
        btnExtractPersona.textContent = "开始提取人设";
    }
});

async function loadPersonaList() {
    renderFileCheckboxes();
    try {
        const res = await fetch(`${API}/api/persona/list`);
        const data = await res.json();
        personaList.innerHTML = "";
        
        if (data.personas.length === 0) {
            personaList.innerHTML = '<p style="color: var(--text-dim); text-align: center; grid-column: 1/-1;">还没有人设，快去提取一个吧～</p>';
            return;
        }
        
        data.personas.forEach(p => {
            const card = document.createElement("div");
            card.className = "persona-card";
            const traits = (p.traits || []).map(t => `<span class="trait-tag">${t}</span>`).join("");
            card.innerHTML = `
                <div class="persona-card-header">
                    <div class="persona-name">${p.name}</div>
                    <span class="trait-tag">ID: ${p.persona_id}</span>
                </div>
                <div class="persona-traits">${traits}</div>
                <div class="persona-info">消息数: ${p.total_messages}</div>
                <div class="persona-actions">
                    <button class="btn btn-ghost" onclick="viewPersona('${p.persona_id}')">查看详情</button>
                    <button class="btn btn-danger" onclick="deletePersona('${p.persona_id}')">删除</button>
                </div>
            `;
            personaList.appendChild(card);
        });
        updateStats();
    } catch (e) {
        console.error(e);
    }
}

async function viewPersona(pid) {
    try {
        const res = await fetch(`${API}/api/persona/${pid}`);
        const data = await res.json();
        const p = data.persona;
        const text = `【${p.name || "未命名"}】\n\n` +
            `性格: ${(p.personality_traits || []).join("、")}\n` +
            `语气: ${p.tone}\n` +
            `语言风格: ${JSON.stringify(p.speech_style)}\n` +
            `常用语: ${(p.common_phrases || []).join("、")}\n` +
            `兴趣: ${(p.interests || []).join("、")}\n` +
            `知识领域: ${(p.knowledge_domains || []).join("、")}\n\n` +
            `=== System Prompt ===\n${p.system_prompt}`;
        alert(text);
    } catch (e) {
        alert("加载失败: " + e.message);
    }
}

async function deletePersona(pid) {
    if (!confirm("确定删除这个人设吗？")) return;
    try {
        await fetch(`${API}/api/persona/${pid}`, { method: "DELETE" });
        loadPersonaList();
    } catch (e) {
        alert("删除失败: " + e.message);
    }
}

// ============ 知识库 ============
async function loadKnowledgeStats() {
    try {
        const res = await fetch(`${API}/api/knowledge/stats`);
        const data = await res.json();
        document.getElementById("ks-total").textContent = data.total_chunks;
        document.getElementById("ks-types").textContent = Object.keys(data.source_types || {}).length;
        document.getElementById("ks-model").textContent = data.using_model ? data.model_name.substring(0, 15) : "TF-IDF";
        updateStats();
    } catch (e) {
        console.error(e);
    }
}

document.getElementById("btn-search").addEventListener("click", async () => {
    const query = document.getElementById("search-query").value.trim();
    if (!query) return;
    
    try {
        const res = await fetch(`${API}/api/knowledge/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query, top_k: 5 }),
        });
        const data = await res.json();
        const container = document.getElementById("search-results");
        container.innerHTML = "";
        
        if (data.results.length === 0) {
            container.innerHTML = '<p style="color: var(--text-dim)">未找到相关内容</p>';
            return;
        }
        
        data.results.forEach(r => {
            const div = document.createElement("div");
            div.className = "search-result-item";
            div.innerHTML = `
                <div class="search-result-meta">
                    <span>${r.source_type} | ${r.source_name}</span>
                    <span class="score-badge">相关度: ${r.score.toFixed(3)}</span>
                </div>
                <div class="search-result-content">${r.content.substring(0, 300)}${r.content.length > 300 ? "..." : ""}</div>
            `;
            container.appendChild(div);
        });
    } catch (e) {
        console.error(e);
    }
});

document.getElementById("btn-clear-knowledge").addEventListener("click", async () => {
    if (!confirm("确定清空整个知识库吗？此操作不可撤销！")) return;
    try {
        await fetch(`${API}/api/knowledge`, { method: "DELETE" });
        parsedFiles = [];
        loadKnowledgeStats();
        alert("知识库已清空");
    } catch (e) {
        alert("清空失败: " + e.message);
    }
});

// ============ 对话测试 ============
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const btnSend = document.getElementById("btn-send");

async function loadChatPersonas() {
    const select = document.getElementById("chat-persona-select");
    try {
        const res = await fetch(`${API}/api/persona/list`);
        const data = await res.json();
        select.innerHTML = '<option value="">请选择人设...</option>';
        data.personas.forEach(p => {
            select.innerHTML += `<option value="${p.persona_id}">${p.name} (${p.persona_id})</option>`;
        });
    } catch (e) {
        console.error(e);
    }
}

btnSend.addEventListener("click", sendMessage);
chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

async function sendMessage() {
    const personaId = document.getElementById("chat-persona-select").value;
    const message = chatInput.value.trim();
    const useKnowledge = document.getElementById("chat-use-knowledge").checked;
    
    if (!personaId) {
        alert("请先选择人设");
        return;
    }
    if (!message) return;
    
    // 添加用户消息
    appendMessage("user", message);
    chatInput.value = "";
    
    try {
        const res = await fetch(`${API}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                persona_id: personaId,
                message,
                use_knowledge: useKnowledge,
                top_k: 5,
            }),
        });
        const data = await res.json();
        
        // 展示构建的prompt和上下文（无LLM时给用户看）
        let reply = "⚠️ 系统未接入LLM，以下是为人设生成的提示词和检索到的上下文：\n\n";
        reply += `【System Prompt】\n${data.system_prompt}\n\n`;
        if (data.retrieved_context) {
            reply += `【检索到的相关记忆】\n${data.retrieved_context}\n\n`;
        }
        reply += "请将上述信息接入你的LLM（如GPT/Claude）生成回复。";
        
        appendMessage("bot", reply);
    } catch (e) {
        appendMessage("bot", "请求失败: " + e.message);
    }
}

function appendMessage(role, content) {
    const div = document.createElement("div");
    div.className = `chat-msg ${role}`;
    div.innerHTML = `
        <div class="msg-avatar">${role === "user" ? "👤" : "🤖"}</div>
        <div class="msg-content">${content}</div>
    `;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ============ 幻象机接入 ============
async function loadPhantomPersonas() {
    const container = document.getElementById("phantom-persona-list");
    try {
        const res = await fetch(`${API}/api/phantom/list`);
        const data = await res.json();
        container.innerHTML = "";
        
        if (data.personas.length === 0) {
            container.innerHTML = '<span class="hint">还没有可用人设</span>';
            return;
        }
        
        data.personas.forEach(p => {
            const div = document.createElement("div");
            div.className = "persona-card";
            div.style.cursor = "pointer";
            div.innerHTML = `
                <div class="persona-card-header">
                    <div class="persona-name">${p.name}</div>
                    <span class="trait-tag">${p.persona_id}</span>
                </div>
                <div class="persona-traits">${(p.traits || []).map(t => `<span class="trait-tag">${t}</span>`).join("")}</div>
                <div class="persona-info">消息数: ${p.total_messages}</div>
            `;
            div.onclick = () => loadPersonaPrompt(p.persona_id);
            container.appendChild(div);
        });
    } catch (e) {
        console.error(e);
    }
}

async function loadPersonaPrompt(pid) {
    try {
        const res = await fetch(`${API}/api/phantom/persona/${pid}`);
        const data = await res.json();
        document.getElementById("prompt-preview").textContent = data.system_prompt;
    } catch (e) {
        document.getElementById("prompt-preview").textContent = "加载失败: " + e.message;
    }
}

// ============ 工具函数 ============
function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
}

async function updateStats() {
    try {
        const res = await fetch(`${API}/api/health`);
        const data = await res.json();
        document.getElementById("stat-chunks").textContent = data.knowledge.total_chunks;
        document.getElementById("stat-personas").textContent = data.persona_count;
    } catch (e) {
        console.error(e);
    }
}

// 初始化
updateStats();
