"""
人设提取引擎
从聊天记录、文档等文本中提取人物画像，用于AI模仿
"""
import re
import json
import random
from collections import Counter
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class PersonaProfile:
    """人物画像"""
    # 基础信息
    name: str = ""
    aliases: List[str] = field(default_factory=list)
    
    # 语言风格
    speech_style: Dict = field(default_factory=dict)  # 语言风格特征
    common_phrases: List[str] = field(default_factory=list)  # 常用语/口头禅
    vocabulary: List[str] = field(default_factory=list)  # 特色词汇
    sentence_length_avg: float = 0.0  # 平均句长
    emoji_usage: List[str] = field(default_factory=list)  # 常用表情
    
    # 性格特征
    personality_traits: List[str] = field(default_factory=list)  # 性格标签
    values: List[str] = field(default_factory=list)  # 价值观
    
    # 兴趣爱好
    interests: List[str] = field(default_factory=list)  # 兴趣爱好
    
    # 知识领域
    knowledge_domains: List[str] = field(default_factory=list)  # 知识领域
    expertise: List[str] = field(default_factory=list)  # 专业领域
    
    # 人际关系
    relationships: List[str] = field(default_factory=list)  # 人际关系
    
    # 语气/情绪倾向
    tone: str = ""  # 整体语气
    emotion_tendency: str = ""  # 情绪倾向
    
    # 对话习惯
    response_patterns: List[str] = field(default_factory=list)  # 回复模式
    question_frequency: float = 0.0  # 提问频率
    
    # 生成的prompt
    system_prompt: str = ""
    
    # 统计信息
    total_messages: int = 0
    word_count: int = 0
    
    def to_dict(self):
        return asdict(self)
    
    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class PersonaExtractor:
    """人设提取器"""
    
    # 常用语气词/口头禅
    FILLER_WORDS = [
        "嗯", "啊", "哦", "哈", "吧", "呢", "嘛", "啦", "呀", "喽",
        "嘿嘿", "哈哈", "嗯嗯", "哦哦", "啊啊",
        "其实", "就是", "然后", "那个", "怎么说",
        "说实话", "讲真", "老实说",
    ]
    
    # 情绪相关词汇
    POSITIVE_WORDS = ["开心", "高兴", "喜欢", "太棒了", "好棒", "赞", "牛", "厉害", "完美", "哈哈", "嘻嘻", "嘿嘿"]
    NEGATIVE_WORDS = ["难过", "伤心", "烦", "郁闷", "生气", "无语", "崩溃", "累", "讨厌", "气死"]
    
    # 常见兴趣领域关键词
    INTEREST_KEYWORDS = {
        "游戏": ["游戏", "打游戏", "上分", "排位", "lol", "王者荣耀", "原神", "吃鸡", "steam", "电竞"],
        "音乐": ["音乐", "听歌", "演唱会", "吉他", "钢琴", "唱歌", "k歌", "专辑", "歌手", "乐队"],
        "电影": ["电影", "看电影", "剧情", "演员", "导演", "上映", "票房", "影评", "番剧", "动漫"],
        "美食": ["吃", "美食", "做饭", "菜谱", "餐厅", "好吃", "料理", "烘焙", "咖啡", "奶茶"],
        "运动": ["运动", "健身", "跑步", "篮球", "足球", "游泳", "瑜伽", "打球", "锻炼"],
        "旅行": ["旅行", "旅游", "出去玩", "景点", "攻略", "酒店", "机票", "打卡", "风景"],
        "阅读": ["看书", "读书", "小说", "书", "作者", "阅读", "推荐书"],
        "科技": ["编程", "代码", "技术", "ai", "算法", "服务器", "linux", "python", "java", "前端", "后端"],
        "摄影": ["拍照", "摄影", "相机", "镜头", "修图", "ps", "滤镜"],
    }
    
    # 知识领域关键词
    DOMAIN_KEYWORDS = {
        "计算机/编程": ["代码", "编程", "函数", "算法", "数据结构", "数据库", "服务器", "api", "接口", "bug", "部署"],
        "设计": ["设计", "ui", "ux", "ps", "figma", "配色", "排版", "原型", "交互"],
        "金融": ["股票", "基金", "投资", "理财", "k线", "涨停", "收益", "风险", "资产"],
        "教育": ["学习", "考试", "课程", "论文", "学校", "老师", "学生", "作业", "知识"],
        "医疗健康": ["医院", "医生", "健康", "运动", "饮食", "睡眠", "体检", "药"],
        "商业": ["项目", "商业", "市场", "用户", "产品", "运营", "增长", "转化", "bp"],
    }
    
    # 性格推断关键词
    PERSONALITY_SIGNALS = {
        "幽默风趣": ["哈哈", "笑死", "开玩笑", "逗你", "梗", "段子", "沙雕", "整活"],
        "严谨理性": ["分析", "数据", "逻辑", "理论", "实际上", "客观来说", "从专业角度"],
        "热情开朗": ["超", "太好", "棒", "喜欢", "爱了", "绝了", "冲冲冲"],
        "内敛稳重": ["嗯", "好的", "可以", "了解", "收到", "明白"],
        "直率坦诚": ["说实话", "实话说", "不瞒你说", "坦白讲"],
        "感性细腻": ["感觉", "心情", "感动", "温暖", "心疼", "感触"],
        "自信强势": ["我觉得", "必须", "肯定", "绝对", "毫无疑问"],
        "随和友善": ["没事", "都可以", "随便", "都行", "你决定"],
    }
    
    def __init__(self):
        self.profile = PersonaProfile()
    
    def extract_from_messages(self, messages: List[Dict]) -> PersonaProfile:
        """
        从聊天消息中提取人设
        messages: [{"time": "...", "sender": "...", "content": "..."}]
        """
        if not messages:
            return self.profile
        
        self.profile.total_messages = len(messages)
        
        # 统计所有发送人
        senders = Counter([m.get("sender", "") for m in messages if m.get("sender")])
        if senders:
            # 取发言最多的人为目标人物
            top_sender = senders.most_common(1)[0][0]
            self.profile.name = top_sender
            self.profile.aliases = [s for s, _ in senders.most_common(5)]
        
        # 提取目标人物的所有消息
        target_messages = [
            m for m in messages 
            if m.get("sender") == self.profile.name
        ]
        
        if not target_messages:
            target_messages = messages  # 如果无法区分，使用全部
        
        all_text = "\n".join([m.get("content", "") for m in target_messages])
        self._analyze_text(all_text, target_messages)
        
        # 生成system prompt
        self.profile.system_prompt = self._generate_system_prompt()
        
        return self.profile
    
    def extract_from_documents(self, documents: List[Dict]) -> PersonaProfile:
        """
        从文档中提取人设
        documents: [{"file_name": "...", "text": "...", "source": "..."}]
        """
        all_text = "\n".join([d.get("text", "") for d in documents])
        self._analyze_text(all_text, [{"content": d.get("text", "")} for d in documents])
        self.profile.system_prompt = self._generate_system_prompt()
        return self.profile
    
    def _analyze_text(self, text: str, messages: List[Dict]):
        """分析文本，提取人设特征"""
        if not text.strip():
            return
        
        contents = [m.get("content", "") for m in messages if m.get("content")]
        self.profile.word_count = len(text)
        
        # 1. 语言风格分析
        self._analyze_speech_style(contents, text)
        
        # 2. 性格特征分析
        self._analyze_personality(text)
        
        # 3. 兴趣爱好分析
        self._analyze_interests(text)
        
        # 4. 知识领域分析
        self._analyze_knowledge_domains(text)
        
        # 5. 情绪倾向分析
        self._analyze_emotion(text)
        
        # 6. 对话习惯分析
        self._analyze_conversation_patterns(contents)
    
    def _analyze_speech_style(self, contents: List[str], full_text: str):
        """分析语言风格"""
        # 句长分析
        sentences = [s.strip() for s in re.split(r'[。！？!?\n]', full_text) if s.strip()]
        if sentences:
            avg_len = sum(len(s) for s in sentences) / len(sentences)
            self.profile.sentence_length_avg = round(avg_len, 1)
        
        # 判断正式/口语化程度
        formal_markers = ["因此", "然而", "综上所述", "基于", "鉴于", "特此"]
        formal_count = sum(full_text.count(w) for w in formal_markers)
        casual_markers = ["哈哈", "啊", "吧", "呢", "嘛", "啦", "呀", "哦", "嗯"]
        casual_count = sum(full_text.count(w) for w in casual_markers)
        
        if formal_count > casual_count:
            formality = "正式书面"
        elif casual_count > formal_count * 2:
            formality = "口语化"
        else:
            formality = "半正式"
        
        # 句末语气词偏好
        end_particles = {}
        for content in contents:
            content = content.strip()
            if content and content[-1] in "吧呢嘛啦呀哦嗯哈啊":
                p = content[-1]
                end_particles[p] = end_particles.get(p, 0) + 1
        
        self.profile.speech_style = {
            "formality": formality,
            "avg_sentence_length": self.profile.sentence_length_avg,
            "preferred_end_particles": dict(sorted(end_particles.items(), key=lambda x: -x[1])[:5]),
        }
        
        # 提取常用语/口头禅
        self._extract_common_phrases(contents)
        
        # 提取表情符号
        emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]|[\U0001F600-\U0001F64F]|[\u2600-\u27BF]|[\u1F300-\u1FAFF]')
        emojis = emoji_pattern.findall(full_text)
        if emojis:
            emoji_counter = Counter(emojis)
            self.profile.emoji_usage = [e for e, _ in emoji_counter.most_common(10)]
        
        # 提取特色词汇（排除停用词后的高频词）
        self._extract_vocabulary(full_text)
    
    def _extract_common_phrases(self, contents: List[str]):
        """提取常用语和口头禅"""
        # 统计句首词
        start_words = []
        for content in contents:
            content = content.strip()
            if len(content) >= 2:
                # 取前2-4个字
                for n in [2, 3, 4]:
                    if len(content) >= n:
                        start_words.append(content[:n])
        
        # 统计高频短句
        short_phrases = [c.strip() for c in contents if 2 <= len(c.strip()) <= 10]
        phrase_counter = Counter(short_phrases)
        
        common = [p for p, c in phrase_counter.most_common(20) if c >= 2]
        self.profile.common_phrases = common[:15]
    
    def _extract_vocabulary(self, text: str):
        """提取特色词汇"""
        try:
            import jieba
            import jieba.analyse
            
            # 使用jieba提取关键词
            keywords = jieba.analyse.extract_tags(text, topK=50, withWeight=False)
            # 过滤单字词
            keywords = [w for w in keywords if len(w) >= 2]
            self.profile.vocabulary = keywords[:30]
        except Exception:
            # 降级：简单词频统计
            words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
            word_counter = Counter(words)
            self.profile.vocabulary = [w for w, c in word_counter.most_common(30) if c >= 2]
    
    def _analyze_personality(self, text: str):
        """分析性格特征"""
        traits = []
        for trait, keywords in self.PERSONALITY_SIGNALS.items():
            count = sum(text.count(k) for k in keywords)
            if count >= 2:
                traits.append(trait)
        
        # 没有匹配到就给个默认
        if not traits:
            traits = ["中性"]
        
        self.profile.personality_traits = traits
    
    def _analyze_interests(self, text: str):
        """分析兴趣爱好"""
        interests = []
        for interest, keywords in self.INTEREST_KEYWORDS.items():
            count = sum(text.count(k) for k in keywords)
            if count >= 2:
                interests.append(interest)
        
        self.profile.interests = interests
    
    def _analyze_knowledge_domains(self, text: str):
        """分析知识领域"""
        domains = []
        expertise = []
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            count = sum(text.count(k) for k in keywords)
            if count >= 3:
                domains.append(domain)
            if count >= 8:
                expertise.append(domain)
        
        self.profile.knowledge_domains = domains
        self.profile.expertise = expertise
    
    def _analyze_emotion(self, text: str):
        """分析情绪倾向"""
        positive_count = sum(text.count(w) for w in self.POSITIVE_WORDS)
        negative_count = sum(text.count(w) for w in self.NEGATIVE_WORDS)
        
        if positive_count > negative_count * 2:
            self.profile.emotion_tendency = "积极乐观"
            self.profile.tone = "活泼热情"
        elif negative_count > positive_count * 2:
            self.profile.emotion_tendency = "偏消极"
            self.profile.tone = "低沉内敛"
        else:
            self.profile.emotion_tendency = "中性平稳"
            self.profile.tone = "平和自然"
    
    def _analyze_conversation_patterns(self, contents: List[str]):
        """分析对话习惯"""
        if not contents:
            return
        
        # 提问频率
        question_count = sum(1 for c in contents if "?" in c or "？" in c)
        self.profile.question_frequency = round(question_count / len(contents), 3)
        
        # 回复模式
        patterns = []
        short_replies = [c.strip() for c in contents if len(c.strip()) <= 5]
        if len(short_replies) > len(contents) * 0.3:
            patterns.append("常用简短回复")
        
        if self.profile.question_frequency > 0.3:
            patterns.append("喜欢提问互动")
        
        if self.profile.question_frequency < 0.1:
            patterns.append("较少提问，偏向陈述")
        
        self.profile.response_patterns = patterns
    
    def _generate_system_prompt(self) -> str:
        """生成用于AI模仿的系统提示词"""
        p = self.profile
        
        parts = []
        parts.append(f"你正在扮演一个人物角色，请严格按照以下人设进行对话：\n")
        
        if p.name:
            parts.append(f"【姓名/昵称】{p.name}")
        
        if p.personality_traits:
            parts.append(f"【性格特征】{'、'.join(p.personality_traits)}")
        
        if p.tone:
            parts.append(f"【整体语气】{p.tone}")
        
        if p.emotion_tendency:
            parts.append(f"【情绪倾向】{p.emotion_tendency}")
        
        if p.speech_style:
            formality = p.speech_style.get("formality", "")
            if formality:
                parts.append(f"【语言风格】{formality}，平均句长约{p.speech_style.get('avg_sentence_length', 0)}字")
        
        if p.common_phrases:
            parts.append(f"【常用语/口头禅】{'、'.join(p.common_phrases[:10])}")
        
        if p.vocabulary:
            parts.append(f"【特色词汇】{'、'.join(p.vocabulary[:15])}")
        
        if p.emoji_usage:
            parts.append(f"【常用表情】{' '.join(p.emoji_usage[:8])}")
        
        if p.interests:
            parts.append(f"【兴趣爱好】{'、'.join(p.interests)}")
        
        if p.knowledge_domains:
            parts.append(f"【知识领域】{'、'.join(p.knowledge_domains)}")
        
        if p.expertise:
            parts.append(f"【专业擅长】{'、'.join(p.expertise)}")
        
        if p.response_patterns:
            parts.append(f"【对话习惯】{'；'.join(p.response_patterns)}")
        
        if p.end_particles if hasattr(p, 'end_particles') else None:
            pass
        
        parts.append("\n【模仿要求】")
        parts.append("1. 保持上述语言风格和语气，不要使用过于正式或学术化的表达")
        parts.append("2. 回复时适当使用口头禅和特色词汇")
        parts.append("3. 保持性格特征一致，不要OOC（out of character）")
        if p.emoji_usage:
            parts.append(f"4. 适当使用常用表情：{' '.join(p.emoji_usage[:5])}")
        parts.append("5. 如果用户问的问题超出你的知识领域，可以诚实地表示不太了解")
        
        return "\n".join(parts)
    
    def save(self, persona_id: str, persona_dir: str):
        """保存人设到文件"""
        import os
        os.makedirs(persona_dir, exist_ok=True)
        file_path = os.path.join(persona_dir, f"{persona_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.profile.to_json())
        return file_path
    
    @staticmethod
    def load(persona_id: str, persona_dir: str) -> Optional[PersonaProfile]:
        """从文件加载人设"""
        import os
        file_path = os.path.join(persona_dir, f"{persona_id}.json")
        if not os.path.exists(file_path):
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        profile = PersonaProfile()
        for k, v in data.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        return profile
