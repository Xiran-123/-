"""
向量知识库（RAG检索）
优先使用 FAISS + sentence-transformers，无依赖时自动降级为 numpy + TF-IDF
"""
import os
import json
import uuid
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class KnowledgeChunk:
    """知识块"""
    chunk_id: str
    source_type: str  # wechat / word / image / video / text
    source_name: str
    content: str
    metadata: Dict = None
    
    def to_dict(self):
        return asdict(self)


class VectorStore:
    """向量存储（支持 FAISS / numpy 双模式）"""
    
    def __init__(self, knowledge_dir: str, model_name: str = "shibing624/text2vec-base-chinese"):
        self.knowledge_dir = knowledge_dir
        self.model_name = model_name
        self.model = None
        self.use_faiss = False
        self.faiss_index = None
        self.numpy_vectors = None  # np.ndarray, shape (n, dim)
        self.chunks: List[KnowledgeChunk] = []
        self._dim = None
        
        os.makedirs(knowledge_dir, exist_ok=True)
        self.index_file = os.path.join(knowledge_dir, "vectors.npy")
        self.meta_file = os.path.join(knowledge_dir, "chunks.json")
        
        self._load_model()
        self._load_existing()
    
    def _load_model(self):
        """加载向量模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            try:
                self._dim = self.model.get_embedding_dimension()
            except AttributeError:
                self._dim = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"[警告] 无法加载向量模型 {self.model_name}: {e}")
            print("将使用TF-IDF降级方案")
            self.model = None
            self._dim = None
    
    def _load_existing(self):
        """加载已有的索引和数据"""
        if os.path.exists(self.meta_file):
            try:
                with open(self.meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chunks = [KnowledgeChunk(**d) for d in data]
            except Exception:
                self.chunks = []
        
        if os.path.exists(self.index_file) and self.chunks:
            try:
                self.numpy_vectors = np.load(self.index_file)
                self._dim = self.numpy_vectors.shape[1]
            except Exception:
                self.numpy_vectors = None
    
    def _encode(self, texts: List[str]) -> np.ndarray:
        """编码文本为向量"""
        if self.model is not None:
            vecs = self.model.encode(texts, normalize_embeddings=True)
            return np.array(vecs, dtype=np.float32)
        else:
            return self._tfidf_encode(texts)
    
    def _tfidf_encode(self, texts: List[str]) -> np.ndarray:
        """TF-IDF降级编码"""
        import re
        from collections import Counter
        
        def tokenize(text):
            return re.findall(r'[\u4e00-\u9fa5]{2,}|[a-zA-Z]{2,}', text.lower())
        
        all_tokens = []
        tokenized = []
        for text in texts:
            tokens = tokenize(text)
            tokenized.append(tokens)
            all_tokens.extend(tokens)
        
        vocab = list(set(all_tokens))
        word_idx = {w: i for i, w in enumerate(vocab)}
        dim = len(vocab)
        
        if dim == 0:
            return np.zeros((len(texts), 1), dtype=np.float32)
        
        doc_freq = Counter()
        for tokens in tokenized:
            for w in set(tokens):
                doc_freq[w] += 1
        
        idf = {}
        for w, df in doc_freq.items():
            idf[w] = np.log(len(texts) / (df + 1)) + 1
        
        vectors = np.zeros((len(texts), dim), dtype=np.float32)
        for i, tokens in enumerate(tokenized):
            tf = Counter(tokens)
            total = len(tokens) or 1
            for w, count in tf.items():
                if w in word_idx:
                    vectors[i, word_idx[w]] = (count / total) * idf.get(w, 1.0)
        
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        vectors = vectors / norms
        
        self._dim = dim
        return vectors
    
    def add_documents(self, source_type: str, source_name: str, contents: List[str], 
                      metadata: Dict = None) -> List[str]:
        """
        添加文档到知识库
        返回添加的chunk_id列表
        """
        chunks = self._split_into_chunks(contents)
        
        new_chunks = []
        for content in chunks:
            chunk = KnowledgeChunk(
                chunk_id=str(uuid.uuid4()),
                source_type=source_type,
                source_name=source_name,
                content=content,
                metadata=metadata or {},
            )
            new_chunks.append(chunk)
        
        if not new_chunks:
            return []
        
        texts = [c.content for c in new_chunks]
        embeddings = self._encode(texts)
        
        # 合并到已有向量
        if self.numpy_vectors is None or self.numpy_vectors.shape[0] == 0:
            self.numpy_vectors = embeddings
        else:
            # 维度对齐
            if embeddings.shape[1] != self.numpy_vectors.shape[1]:
                # 重新编码所有（TF-IDF词表变化时）
                all_texts = [c.content for c in self.chunks] + texts
                self.numpy_vectors = self._encode(all_texts)
            else:
                self.numpy_vectors = np.vstack([self.numpy_vectors, embeddings])
        
        self.chunks.extend(new_chunks)
        self._save()
        
        return [c.chunk_id for c in new_chunks]
    
    def _split_into_chunks(self, contents: List[str], 
                           chunk_size: int = 500, 
                           overlap: int = 50) -> List[str]:
        """将文本分块"""
        chunks = []
        for content in contents:
            if len(content) <= chunk_size:
                if content.strip():
                    chunks.append(content.strip())
            else:
                sentences = self._split_sentences(content)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) <= chunk_size:
                        current += sent
                    else:
                        if current.strip():
                            chunks.append(current.strip())
                        if overlap > 0:
                            current = current[-overlap:] + sent
                        else:
                            current = sent
                if current.strip():
                    chunks.append(current.strip())
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割"""
        import re
        sentences = re.split(r'(?<=[。！？!?；;\n])', text)
        return [s for s in sentences if s.strip()]
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[KnowledgeChunk, float]]:
        """
        检索相关知识块
        返回 [(chunk, score), ...]
        """
        if not self.chunks or self.numpy_vectors is None or self.numpy_vectors.shape[0] == 0:
            return []
        
        if self.model is not None:
            # 使用向量模型，维度固定
            query_vec = self._encode([query])
            scores = np.dot(self.numpy_vectors, query_vec.T).flatten()
        else:
            # TF-IDF模式：查询与所有chunks一起编码，保证词表一致
            all_texts = [c.content for c in self.chunks] + [query]
            all_vecs = self._encode(all_texts)
            self.numpy_vectors = all_vecs[:-1]  # 更新存储向量
            query_vec = all_vecs[-1:]           # 最后一个是查询向量
            scores = np.dot(self.numpy_vectors, query_vec.T).flatten()
        
        # 获取top_k
        k = min(top_k, len(scores))
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = []
        for idx in top_indices:
            results.append((self.chunks[idx], float(scores[idx])))
        
        return results
    
    def _save(self):
        """保存索引和元数据"""
        if self.numpy_vectors is not None:
            try:
                np.save(self.index_file, self.numpy_vectors)
            except Exception:
                pass
        
        try:
            with open(self.meta_file, "w", encoding="utf-8") as f:
                json.dump([c.to_dict() for c in self.chunks], f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_stats(self) -> Dict:
        """获取知识库统计"""
        source_types = {}
        for c in self.chunks:
            source_types[c.source_type] = source_types.get(c.source_type, 0) + 1
        
        return {
            "total_chunks": len(self.chunks),
            "source_types": source_types,
            "vector_dim": self._dim,
            "using_model": self.model is not None,
            "model_name": self.model_name if self.model else "tfidf-fallback",
        }
    
    def clear(self):
        """清空知识库"""
        self.chunks = []
        self.numpy_vectors = None
        if os.path.exists(self.index_file):
            os.remove(self.index_file)
        if os.path.exists(self.meta_file):
            os.remove(self.meta_file)
