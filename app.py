import os
import threading
import openai
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ GPT 연결된 Flask 서버입니다!"

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

        # 최대 5초 대기
        for _ in range(5):
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break

    except Exception as e:
        print(f"[GPT 처리 오류] {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        user_input = request.get_json()
        utterance = user_input['userRequest']['utterance']

        # GPT 처리는 비동기적으로 실행
        threading.Thread(target=run_gpt_thread, args=(utterance,)).start()

        # 우선 응답
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

if __name__ == "__main__":
    app.run()