from flask import Flask, request, jsonify
import openai
import time

app = Flask(__name__)
import os
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = "asst_KisGSVwT5ohNn88A6JK9qCeX"  # 실제 Assistant ID로 바꿔야 함

@app.route("/webhook", methods=["POST"])
def webhook():
    user_input = request.json['userRequest']['utterance']

    thread = openai.beta.threads.create()
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input
    )
    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=ASSISTANT_ID
    )

    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        time.sleep(1)

    messages = openai.beta.threads.messages.list(thread_id=thread.id)
    answer = messages.data[0].content[0].text.value

    return jsonify({
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": answer
                }
            }]
        }
    })

@app.route("/", methods=["GET"])
def home():
    return "✅ Render Flask 서버 정상 작동 중입니다!"
