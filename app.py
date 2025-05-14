import os
import threading
import openai
import time
from flask import Flask, request, jsonify, render_template_string
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__)

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
            lines = f.read()
            return lines or "🤖 후비 답변: 아직 생성된 응답이 없습니다."
    except FileNotFoundError:
        return "🤖 후비 답변: 아직 응답 기록이 없습니다."

@app.route("/")
def home():
    return "✅ GPT 연결된 Flask 서버입니다!"

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

# ✅ 웹 페이지로 결과 보여주는 라우트
@app.route("/response")
def response_page():
    try:
        with open("responses.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "아직 응답 기록이 없습니다."

    html_template = """
    <!DOCTYPE html>
    <html lang=\"ko\">
    <head>
        <meta charset=\"UTF-8\">
        <title>후비 GPT 응답 기록</title>
        <style>
            body { font-family: sans-serif; padding: 2rem; background-color: #f9f9f9; }
            .box { background: #fff; padding: 2rem; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <h1>🤖 후비 GPT 응답 기록</h1>
        <div class=\"box\">{{ content }}</div>
    </body>
    </html>
    """
    return render_template_string(html_template, content=content)

if __name__ == "__main__":
    app.run()
