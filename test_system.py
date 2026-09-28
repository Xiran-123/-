"""测试脚本：验证完整流程"""
import sys
import os
import json
import urllib.request
import urllib.parse

BASE = "http://localhost:8000"

def test_health():
    print("=" * 50)
    print("1. 健康检查")
    with urllib.request.urlopen(f"{BASE}/api/health") as r:
        data = json.loads(r.read())
        print(json.dumps(data, ensure_ascii=False, indent=2))

def test_upload():
    print("\n" + "=" * 50)
    print("2. 上传并解析微信聊天记录")
    boundary = "----TestBoundary"
    filepath = os.path.join(os.path.dirname(__file__), "examples", "sample_wechat.txt")
    
    with open(filepath, "rb") as f:
        file_content = f.read()
    
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="test_chat.txt"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode() + file_content + f"\r\n--{boundary}--\r\n".encode()
    
    req = urllib.request.Request(
        f"{BASE}/api/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return data

def test_extract_persona():
    print("\n" + "=" * 50)
    print("3. 提取人设")
    payload = json.dumps({
        "files": ["test_chat.txt"],
        "persona_name": "测试人设",
        "target_sender": "小红"
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/api/persona/extract",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        print(f"人设ID: {data['persona_id']}")
        persona = data["persona"]
        print(f"姓名: {persona['name']}")
        print(f"性格: {persona['personality_traits']}")
        print(f"兴趣: {persona['interests']}")
        print(f"语气: {persona['tone']}")
        print(f"常用语: {persona['common_phrases']}")
        print(f"知识领域: {persona['knowledge_domains']}")
        print("\n--- System Prompt ---")
        print(persona["system_prompt"])
        return data["persona_id"]

def test_knowledge_search():
    print("\n" + "=" * 50)
    print("4. 知识库检索")
    payload = json.dumps({"query": "咖啡", "top_k": 3}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/knowledge/search",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        for item in data["results"]:
            print(f"  [{item['source_name']}] 相似度:{item['score']:.3f}")
            print(f"  {item['content'][:80]}")
            print()

def test_phantom_api(persona_id):
    print("\n" + "=" * 50)
    print("5. 幻象机接入API测试")
    # 列表
    with urllib.request.urlopen(f"{BASE}/api/phantom/list") as r:
        data = json.loads(r.read())
        print(f"人设列表: {len(data['personas'])} 个")
    
    # 获取prompt
    with urllib.request.urlopen(f"{BASE}/api/phantom/persona/{persona_id}") as r:
        data = json.loads(r.read())
        print(f"获取人设prompt成功，长度: {len(data['system_prompt'])}")
    
    # 获取上下文
    payload = json.dumps({"query": "一起出去玩", "top_k": 3}).encode()
    req = urllib.request.Request(
        f"{BASE}/api/phantom/context/{persona_id}",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read())
        print(f"检索到 {len(data['context'])} 条相关记忆")

if __name__ == "__main__":
    try:
        test_health()
        test_upload()
        pid = test_extract_persona()
        test_knowledge_search()
        test_phantom_api(pid)
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！系统运行正常。")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
