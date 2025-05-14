import os
from flask import Flask, request, jsonify
import openai
import time
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ GPT 연결된 Flask 서버입니다!"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        user_input = request.get_json()
        utterance = user_input['userRequest']['utterance']

        # GPT Assistant: thread 생성
        thread = openai.beta.threads.create()
        thread_id = thread.id

        # 사용자 발화 메시지 추가
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=utterance
        )

        # GPT 실행
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # 실행 완료 대기 (최대 10초 루프)
        for _ in range(10):
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break
            time.sleep(1)
        else:
            return jsonify({
                "version": "2.0",
                "template": {
                    "outputs": [
                        {"simpleText": {"text": "⚠️ GPT 응답 시간이 초과되었습니다."}}
                    ]
                }
            })

        # 응답 추출
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        answer = messages.data[0].content[0].text.value

        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": answer}}
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