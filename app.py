import os
import time
import openai
from flask import Flask, request, jsonify, render_template, send_from_directory, session
from dotenv import load_dotenv

# .env 파일의 환경변수 불러오기
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "hubi-temp-secret")

@app.route("/install")
def install():
    session.clear()
    return render_template("install.html")

@app.route("/ask", methods=["POST"])
def ask():
    try:
        message = request.json.get("message", "")

        # Thread가 없으면 새로 생성
        if "thread_id" not in session:
            thread = openai.beta.threads.create()
            session["thread_id"] = thread.id
        thread_id = session["thread_id"]

        # 사용자 메시지 추가
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        # GPT Assistant 실행
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # 완료까지 최대 30초 대기
        for _ in range(30):
            status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if status.status == "completed":
                break
            time.sleep(1)

        # 마지막 assistant 응답 찾기
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        answer = None

        for msg in reversed(messages.data):
            if msg.role == "assistant":
                for part in msg.content:
                    if part.type == "text" and part.text.value.strip():
                        answer = part.text.value.strip()
                        break
                if answer:
                    break

        if not answer:
            answer = "죄송합니다. 응답을 생성하지 못했어요."

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"answer": f"오류 발생: {str(e)}"})

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run()