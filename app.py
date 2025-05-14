import os
import threading
import openai
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__)

# ✅ GPT 응답 저장 함수
def save_response_log(utterance, answer):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("responses.txt", "w", encoding="utf-8") as f:
        f.write(f"[{now}] 사용자: {utterance}\n→ GPT: {answer}\n")

# ✅ 최근 GPT 응답 불러오기 함수
def load_latest_response():
    try:
        with open("responses.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in reversed(lines):
                if line.startswith("→ GPT:"):
                    return line.replace("→ GPT:", "🤖 후비 답변:").strip()
        return "🤖 후비 답변: 아직 생성된 응답이 없습니다."
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

        # ➊ 만약 사용자가 'go'라고 말한 경우, 저장된 응답 제공
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

        # ➋ 일반 발화인 경우, GPT 처리 시작 → 비동기로 처리하고 즉시 응답
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

if __name__ == "__main__":
    app.run()