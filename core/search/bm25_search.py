import math
from collections import defaultdict
import jieba

class BM25:
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.corpus = []
        self.doc_lengths = []
        self.avgdl = 0
        self.doc_freqs = defaultdict(int)
        self.idf = {}
      

    def add_corpus(self, corpus):
        self.corpus = [list(jieba.cut(doc)) for doc in corpus]
        self.doc_lengths = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths)
        self.initialize()

    def initialize(self):
        # 计算每个词的文档频率
        for doc in self.corpus:
            seen = set()
            for word in doc:
                if word not in seen:
                    self.doc_freqs[word] += 1
                    seen.add(word)

        # 计算IDF（逆文档频率）
        num_docs = len(self.corpus)
        for word, freq in self.doc_freqs.items():
            self.idf[word] = math.log((num_docs - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query, doc_index):
        score = 0.0
        doc_length = self.doc_lengths[doc_index]
        for word in query:
            if word not in self.corpus[doc_index]:
                continue
            tf = self.corpus[doc_index].count(word)
            numerator = self.idf[word] * tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avgdl))
            score += numerator / denominator
        return score

    def get_scores(self, query):
        query = list(jieba.cut(query))  # 对查询文本分词
        scores = [self.score(query, i) for i in range(len(self.corpus))]
        return scores


# 示例用法
corpus = [
    "今天天气真好，适合出去玩。",
    "我喜欢学习新知识，尤其是人工智能。",
    "天气好的时候，我喜欢去公园散步。",
    "人工智能是未来的发展方向。"
]

bm25 = BM25(corpus)
query = "天气真好"
scores = bm25.get_scores(query)
print(scores)