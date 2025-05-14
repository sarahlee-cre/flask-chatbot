import os
import json
import time
from flask import Flask, request, jsonify, render_template_string
import openai
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

        # ✅ 1차 응답 (즉시)
        response = {
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": "🤖 GPT 응답을 생성 중이에요. 잠시만 기다려주세요!"}}
                ]
            }
        }

        # ✅ GPT 비동기 실행을 위한 사전 작업
        thread = openai.beta.threads.create()
        thread_id = thread.id
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=utterance
        )

        start_time = time.time()
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        for _ in range(10):
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == "completed":
                break
            time.sleep(1)
        else:
            answer = "⚠️ GPT 응답 시간이 초과되었습니다."
            elapsed = "-"

        # ✅ GPT 응답 추출
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        answer = messages.data[0].content[0].text.value
        elapsed = f"{round(time.time() - start_time, 2)}초"

        # ✅ 응답 내용 로그 저장
        with open("response_log.json", "w", encoding="utf-8") as f:
            json.dump({
                "question": utterance,
                "answer": answer,
                "elapsed_time": elapsed
            }, f, ensure_ascii=False, indent=2)

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": f"❌ 오류 발생: {str(e)}"}}
                ]
            }
        })

# ✅ GPT 결과 웹페이지 출력 (/go)
@app.route("/go")
def show_gpt_response():
    try:
        with open("response_log.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {
            "question": "아직 질문이 없습니다.",
            "answer": "아직 생성된 답변이 없습니다.",
            "elapsed_time": "-"
        }

    html_template = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>후비 GPT 응답</title>
        <style>
            body { font-family: sans-serif; padding: 2rem; background-color: #f9f9f9; }
            .box { background: #fff; padding: 2rem; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
            h1 { color: #222; }
            p { font-size: 1.1rem; margin-bottom: 1rem; }
            strong { color: #444; }
        </style>
    </head>
    <body>
        <h1>🤖 후비 GPT 응답</h1>
        <div class="box">
            <p><strong>질문:</strong> {{ question }}</p>
            <p><strong>답변:</strong> {{ answer }}</p>
            <p><strong>응답 시간:</strong> {{ elapsed_time }}</p>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template, **data)

if __name__ == "__main__":
    app.run()
