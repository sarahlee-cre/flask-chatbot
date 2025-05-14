import os
import threading
import openai
import time
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__, static_folder="static")

# ✅ GPT 응답 저장 함수
def save_response_log(utterance, answer):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elapsed = round(time.time() - start_time, 2)
    with open("responses.txt", "w", encoding="utf-8") as f:
        f.write(f"[시간] {now}\n[질문] {utterance}\n[답변] {answer}\n[응답 시간] {elapsed}초\n")

# ✅ 최근 GPT 응답 불러오기 함수
def load_latest_response():
    try:
        with open("responses.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            question = ""
            answer = ""
            for line in lines:
                if line.startswith("[질문]"):
                    question = line.replace("[질문]", "질문:").strip()
                elif line.startswith("[답변]"):
                    answer = line.replace("[답변]", "🤖 후비 답변:").strip()
            return f"{question}\n{answer}"
    except FileNotFoundError:
        return "🤖 후비 답변: 아직 응답 기록이 없습니다."

@app.route("/install")
def install_page():
    html_template = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="theme-color" content="#ffffff">
        <link rel="manifest" href="/static/manifest.json">
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap">
        <title>후비 챗봇 설치</title>
        <script>
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                    navigator.serviceWorker.register('/static/sw.js');
                });
            }
        </script>
        <style>
            body { font-family: 'Noto Sans KR', sans-serif; text-align: center; padding: 2rem; background-color: #f4f4f4; }
            h1 { margin-bottom: 1rem; }
            p { font-size: 1.2rem; color: #333; }
        </style>
    </head>
    <body>
        <h1>🤖 HUBI GPT 챗봇</h1>
        <p>PWA 설치가 가능한 챗봇입니다.<br>홈 화면에 추가하여 앱처럼 사용할 수 있어요!</p>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        user_input = request.get_json()
        utterance = user_input['userRequest']['utterance'].strip().lower()

        if utterance == "go":
            latest_response = load_latest_response()
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [
                        {"simpleText": {"text": latest_response}}
                    ]
                }
            })

        threading.Thread(target=run_gpt_thread, args=(utterance,)).start()

        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": "🤖 GPT 응답을 생성 중이에요. 잠시만 기다려주세요!"}}
                ]
            }
        })

    except Exception as e:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": f"❌ 오류 발생: {str(e)}"}}
                ]
            }
        })

# ✅ GPT 생성 비동기 함수
def run_gpt_thread(utterance):
    try:
        global start_time
        start_time = time.time()

        thread = openai.beta.threads.create()
        thread_id = thread.id

        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=utterance
        )

        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        for _ in range(10):
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break
            time.sleep(1)

        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        answer = messages.data[0].content[0].text.value

        save_response_log(utterance, answer)

    except Exception as e:
        save_response_log(utterance, f"[GPT 오류] {str(e)}")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run()
