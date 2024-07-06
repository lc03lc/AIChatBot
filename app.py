# coding:utf-8

import base64
import glob
import json
import os
import uuid

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit

from Interact import Llama, Llava  # 导入新的Llava模块
from tools.recommender import Recommend
from tools.text2voice import text2voice
from tools.voice2text import voice2text
from tools import summaryTitle

# clear_folder()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app)

CACHE_DIR = "static/cache"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/text2voice', methods=['POST'])
def text_to_voice_route():
    text = request.form['text']
    audio_filename = f"{CACHE_DIR}/{uuid.uuid4()}.mp3"
    text2voice(text, audio_filename)
    return jsonify(audio_url=f'/{audio_filename}')


@app.route('/voice2text', methods=['POST'])
def voice_to_text_route():
    try:
        text = voice2text()
        return jsonify(text=text)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/save_chat', methods=['POST'])
def save_chat():
    data = request.json
    chat_id = uuid.uuid4()
    chat_file = f"{CACHE_DIR}/{chat_id}.txt"
    with open(chat_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    return jsonify(chat_id=str(chat_id))


@app.route('/load_chats', methods=['GET'])
def load_chats():
    chat_files = glob.glob(f"{CACHE_DIR}/*.txt")
    chats = []
    for chat_file in chat_files:
        with open(chat_file, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
            chat_id = os.path.basename(chat_file).split('.')[0]
            chats.append({"id": chat_id, "timestamp": chat_data.get("timestamp", "未知时间")})
    return jsonify(chats=chats)


@app.route('/load_chat/<chat_id>', methods=['GET'])
def load_chat(chat_id):
    chat_file = f"{CACHE_DIR}/{chat_id}.txt"
    if os.path.exists(chat_file):
        with open(chat_file, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        return jsonify(chat_data)
    else:
        return jsonify(error="Chat not found"), 404


@app.route('/delete_chat/<chat_id>', methods=['DELETE'])
def delete_chat(chat_id):
    chat_file = f"{CACHE_DIR}/{chat_id}.txt"
    if os.path.exists(chat_file):
        os.remove(chat_file)
        return jsonify(success=True)
    else:
        return jsonify(error="Chat not found"), 404


@app.route('/recommendations', methods=['POST'])
def recommendations():
    try:
        data = request.json
        latest_message = data.get('latest_message', '')
        recommendations = Recommend(latest_message)
        return jsonify(recommendations=recommendations)
    except Exception as e:
        print(Exception)
        return jsonify(error=str(e)), 500


@app.route('/rename_chat/<chat_id>', methods=['POST'])
def rename_chat(chat_id):
    data = request.json
    new_name = data.get('newName', '未知时间')
    chat_file = f"{CACHE_DIR}/{chat_id}.txt"
    if os.path.exists(chat_file):
        with open(chat_file, 'r', encoding='utf-8') as f:
            chat_data = json.load(f)
        chat_data['timestamp'] = new_name
        with open(chat_file, 'w', encoding='utf-8') as f:
            json.dump(chat_data, f, ensure_ascii=False)
        return jsonify(success=True)
    else:
        return jsonify(error="Chat not found"), 404


@app.route('/generate_title', methods=['POST'])
def generate_title():
    data = request.json
    messages = data.get("messages", [])

    # 提取用户消息内容
    user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]
    q = f"根据以下内容总结一个提问的问题的总结，不需要标点符号，10个字以内：{user_messages}"
    res = summaryTitle.request_model([summaryTitle.create_message(
        "user", q)])
    title = res["message"]["content"]

    return jsonify({"title": title})


@socketio.on('send_message')
def handle_send_message(data):
    messages = data['messages']
    user_message = data['message']
    model = data.get('model', 'Llama')
    mode = data.get('mode', 'default')  # 获取前端传来的模式，默认为default

    if not messages:
        if mode == 'kids':
            messages.append(Llama.create_message("system", "你现在扮演一个智能语音机器人，并且只能用中文交流。你的目标用户是儿童，所以请用简单、友好和有趣的方式回答他们的问题。使用他们能够理解的词汇和语法，尽量多使用生动的描述和比喻。回答要积极、鼓励并充满热情。如果他们问到复杂的问题，请尝试用简单的例子和故事来解释。避免使用专业术语和过于复杂的语言，确保你的回答是安全和适龄的。"))
        elif mode == 'language-translation':
            messages.append(Llama.create_message("system", "你现在扮演一个语言翻译助手，可以将用户输入的文本翻译成指定的目标语言。"))
        elif mode == 'news-update':
            messages.append(Llama.create_message("system", "你现在扮演一个新闻助手，可以提供最新的新闻更新。请根据用户的需求提供相关的新闻内容。"))
        elif mode == 'math-calculation':
            messages.append(Llama.create_message("system", "你现在扮演一个数学助手，可以帮助用户进行各种数学计算。请提供详细的步骤和解释。"))
        elif mode == 'recipe-recommendation':
            messages.append(Llama.create_message("system", "你现在扮演一个食谱助手，可以根据用户提供的食材和偏好推荐食谱。请确保推荐的食谱简单易懂且易于操作。"))
        elif mode == 'wiki-qa':
            messages.append(Llama.create_message("system", "你现在扮演一个百科全书助手，可以回答各种知识问题。请确保你的回答准确且易于理解。"))
        elif mode == 'entertainment-suggestions':
            messages.append(Llama.create_message("system", "你现在扮演一个娱乐助手，可以根据用户的兴趣推荐电影、电视剧、音乐和书籍。请提供详细的推荐理由和信息。"))
        elif mode == 'health-advice':
            messages.append(Llama.create_message("system", "你现在扮演一个健康助手，可以提供健康和健身相关的建议。请确保你的建议科学且易于理解和操作。"))
        else:
            messages.append(Llama.create_message("system", "你现在扮演一个智能语音机器人，并且只能用中文交流。"))

    messages.append(Llama.create_message("user", user_message))
    emit('receive_message', {'role': 'user', 'content': user_message, 'isImage': False})

    assistant_message = ""
    if model == 'Llava':
        for word in Llava.stream_model(messages):
            assistant_message += word
            emit('receive_message', {'role': 'assistant', 'content': assistant_message, 'isImage': False},
                 broadcast=True)
    else:
        for word in Llama.stream_model(messages):
            assistant_message += word
            emit('receive_message', {'role': 'assistant', 'content': assistant_message, 'isImage': False},
                 broadcast=True)


@socketio.on('send_image')
def handle_send_image(data):
    messages = data['messages']
    image_base64 = data['image']
    user_message = data['message']
    model = data.get('model', 'Llava')
    mode = data.get('mode', 'default')

    if not messages:
        if mode == 'kids':
            messages.append(Llama.create_message("system", "你现在扮演一个智能语音机器人，并且只能用中文交流。你的目标用户是儿童，所以请用简单、友好和有趣的方式回答他们的问题。使用他们能够理解的词汇和语法，尽量多使用生动的描述和比喻。回答要积极、鼓励并充满热情。如果他们问到复杂的问题，请尝试用简单的例子和故事来解释。避免使用专业术语和过于复杂的语言，确保你的回答是安全和适龄的。"))
        elif mode == 'language-translation':
            messages.append(Llama.create_message("system", "你现在扮演一个语言翻译助手，可以将用户输入的文本翻译成指定的目标语言。"))
        elif mode == 'news-update':
            messages.append(Llama.create_message("system", "你现在扮演一个新闻助手，可以提供最新的新闻更新。请根据用户的需求提供相关的新闻内容。"))
        elif mode == 'math-calculation':
            messages.append(Llama.create_message("system", "你现在扮演一个数学助手，可以帮助用户进行各种数学计算。请提供详细的步骤和解释。"))
        elif mode == 'recipe-recommendation':
            messages.append(Llama.create_message("system", "你现在扮演一个食谱助手，可以根据用户提供的食材和偏好推荐食谱。请确保推荐的食谱简单易懂且易于操作。"))
        elif mode == 'wiki-qa':
            messages.append(Llama.create_message("system", "你现在扮演一个百科全书助手，可以回答各种知识问题。请确保你的回答准确且易于理解。"))
        elif mode == 'entertainment-suggestions':
            messages.append(Llama.create_message("system", "你现在扮演一个娱乐助手，可以根据用户的兴趣推荐电影、电视剧、音乐和书籍。请提供详细的推荐理由和信息。"))
        elif mode == 'health-advice':
            messages.append(Llama.create_message("system", "你现在扮演一个健康助手，可以提供健康和健身相关的建议。请确保你的建议科学且易于理解和操作。"))
        else:
            messages.append(Llama.create_message("system", "你现在扮演一个智能语音机器人，并且只能用中文交流。"))

    image_content = base64.b64decode(image_base64)
    image_path = f"{CACHE_DIR}/{uuid.uuid4()}.png"
    with open(image_path, "wb") as image_file:
        image_file.write(image_content)

    if user_message:
        messages.append(Llava.create_message("user", user_message))
        emit('receive_message', {'role': 'user', 'content': user_message, 'isImage': False})

    messages.append(Llava.create_message("user", "用中文描述图片中的内容", image=[image_base64]))
    emit('receive_message', {'role': 'user', 'content': image_base64, 'isImage': True})

    assistant_message = ""
    if model == 'Llava':
        for word in Llava.stream_model(messages):
            assistant_message += word
            emit('receive_message', {'role': 'assistant', 'content': assistant_message, 'isImage': False},
                 broadcast=True)
    else:
        for word in Llama.stream_model(messages):
            assistant_message += word
            emit('receive_message', {'role': 'assistant', 'content': assistant_message, 'isImage': False},
                 broadcast=True)


if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True, host="0.0.0.0", port=5001)
