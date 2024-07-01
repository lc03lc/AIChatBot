from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import requests
import json
import os
from tools.text2voice import text2voice
from tools.clearCache import clear_folder
from tools.voice2text import voice2text
from Interact import Llama, Llava  # 导入新的Llava模块
import uuid
import base64
import glob

clear_folder()

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

@socketio.on('send_message')
def handle_send_message(data):
    messages = data['messages']
    user_message = data['message']
    model = data.get('model', 'Llama')  # 获取前端传来的模型名称，默认为Llama

    if not messages:
        messages.append(Llama.create_message("system", "你现在扮演一个智能语音机器人，并且只能用中文交流。"))

    messages.append(Llama.create_message("user", user_message))
    emit('receive_message', {'role': 'user', 'content': user_message, 'isImage': False})

    assistant_message = ""
    if model == 'Llava':
        for word in Llava.stream_model(messages):  # 使用Llava模块
            assistant_message += word
            emit('receive_message', {'role': 'assistant', 'content': assistant_message, 'isImage': False}, broadcast=True)
    else:
        for word in Llama.stream_model(messages):  # 使用Llama模块
            assistant_message += word
            emit('receive_message', {'role': 'assistant', 'content': assistant_message, 'isImage': False}, broadcast=True)

@socketio.on('send_image')
def handle_send_image(data):
    messages = data['messages']
    image_base64 = data['image']
    user_message = data['message']  # 获取用户消息
    model = data.get('model', 'Llava')  # 获取前端传来的模型名称，默认为Llava

    if not messages:
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
        for word in Llava.stream_model(messages):  # 使用Llava模块
            assistant_message += word
            emit('receive_message', {'role': 'assistant', 'content': assistant_message, 'isImage': False}, broadcast=True)
    else:
        for word in Llama.stream_model(messages):  # 使用Llama模块
            assistant_message += word
            emit('receive_message', {'role': 'assistant', 'content': assistant_message, 'isImage': False}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
