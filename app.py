import os
import threading
import openai
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ GPT 연결된 Flask 서버입니다!"

# ✅ GPT 비동기 실행 및 파일 저장
def run_gpt_thread(utterance):
    try:
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

        for _ in range(5):
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break
            time.sleep(1)

        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        answer = messages.data[0].content[0].text.value

        elapsed = round(time.time() - start_time, 2)

        with open("gpt_response.txt", "w", encoding="utf-8") as f:
            f.write(f"[입력]\n{utterance}\n\n[응답]\n{answer}\n\n[소요 시간] {elapsed}초")

    except Exception as e:
        with open("gpt_response.txt", "w", encoding="utf-8") as f:
            f.write(f"[GPT 오류] {str(e)}")

# ✅ Webhook 요청 응답
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        user_input = request.get_json()
        utterance = user_input['userRequest']['utterance']

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

# ✅ 저장된 GPT 응답을 웹에서 확인하는 경로
@app.route("/response", methods=["GET"])
def response_view():
    try:
        with open("gpt_response.txt", "r", encoding="utf-8") as f:
            content = f.read()
        return f"<pre>{content}</pre>"
    except Exception as e:
        return f"파일을 불러올 수 없습니다: {str(e)}"

if __name__ == "__main__":
    app.run()