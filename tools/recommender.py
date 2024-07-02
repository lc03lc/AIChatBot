import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import json
import jieba
from transformers import BertTokenizer, BertModel
import torch
from tools.plugin_newsTop import get_trending_news

# 加载BERT模型和分词器
tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
model = BertModel.from_pretrained('bert-base-chinese')


def embed_texts(texts):
    inputs = tokenizer(texts, return_tensors='pt', padding=True, truncation=True, max_length=512)
    outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).detach().numpy()


def guess_next_queries(history, news, user_weight=2.0, news_weight=1.95, top_n=4):
    # 合并历史记录和新闻
    all_texts = history + news

    # 获取嵌入向量
    embeddings = embed_texts(all_texts)

    # 计算历史记录和新闻之间的余弦相似度
    cosine_similarities = cosine_similarity(embeddings)

    # 初始化权重
    weights = np.ones(len(all_texts))
    weights[:len(history)] *= user_weight  # 用户历史记录权重
    weights[len(history):] *= news_weight  # 新闻权重

    # 对相似度矩阵进行加权
    weighted_similarities = cosine_similarities * weights[:, np.newaxis]

    # 对每条记录的相似度进行求和，以确定最常讨论的话题
    sum_similarities = weighted_similarities.sum(axis=1)

    # 找出最相似的对话，排除重复的内容
    recommendations = []
    seen = set()
    for idx in sum_similarities.argsort()[::-1]:  # 从高到低排序
        if all_texts[idx] not in seen:
            seen.add(all_texts[idx])
            recommendations.append(all_texts[idx])
            if len(recommendations) == top_n:
                break

    return recommendations


def extract_user_questions(cache_dir):
    user_questions = []

    # 遍历cache文件夹中的所有文件
    for filename in os.listdir(cache_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(cache_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as file:
                data = json.load(file)
                messages = data.get('messages', [])
                for message in messages:
                    if message['role'] == 'user':
                        user_questions.append(message['content'])

    return user_questions


def Recommend(latest_message=""):
    # 指定cache文件夹路径
    cache_dir = 'static/cache'

    # 提取用户提问记录
    chat_history = extract_user_questions(cache_dir)

    # 添加最新消息到历史记录中
    if latest_message:
        chat_history.append(latest_message)

    # 获取头条新闻
    news = get_trending_news()
    news_titles = [item['name'] for item in news]

    # 获取推荐结果
    recommendations = guess_next_queries(chat_history, news_titles)

    return recommendations
