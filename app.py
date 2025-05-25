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

        # 처음 접속 시 Thread 생성
        if "thread_id" not in session:
            thread = openai.beta.threads.create()
            session["thread_id"] = thread.id
        thread_id = session["thread_id"]

        # 사용자 메시지 전송
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        # Assistant 실행
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # 응답 대기 (최대 30초)
        for _ in range(30):
            status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if status.status == "completed":
                break
            time.sleep(1)

        # 메시지 리스트 받아오기
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        print("--- 전체 메시지 로그 ---")
        for msg in messages.data:
            print(f"{msg.role}:", msg.content)

        # 최신 assistant 메시지 중 가장 최근 응답 추출
        assistant_messages = [msg for msg in messages.data if msg.role == "assistant"]
        assistant_messages.sort(key=lambda x: x.created_at, reverse=True)

        answer = None
        for msg in assistant_messages:
            for part in msg.content:
                if part.type == "text" and part.text.value.strip():
                    answer = part.text.value.strip()
                    break
            if answer:
                break

        if not answer:
            answer = "죄송합니다. 아직 적절한 답변을 찾지 못했어요. 다시 질문해 주세요."

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"answer": f"오류 발생: {str(e)}"})

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render에서 주는 포트 사용
    app.run(host="0.0.0.0", port=port)
