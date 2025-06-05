import os
import time
import openai
import threading
import uuid
from flask import Flask, request, jsonify, render_template, send_from_directory, session
from dotenv import load_dotenv

# .env 파일의 환경변수 불러오기
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "hubi-temp-secret")

# 사용자별 응답 저장소
response_store = {}  # session_id: 응답 문자열

@app.route("/")
def home():
    return render_template("install.html")

@app.route("/install")
def install():
    session.clear()
    return render_template("install.html")

def fetch_assistant_response(message, session_id, thread_id):
    try:
        # ✅ 기존 run이 존재하는지 확인
        runs = openai.beta.threads.runs.list(thread_id=thread_id, limit=1)
        if runs.data and runs.data[0].status in ["queued", "in_progress"]:
            response_store[session_id] = "이전 질문 응답이 아직 처리 중입니다. 잠시 후 다시 시도해 주세요."
            return

        # ✅ 사용자 메시지 전송
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        # ✅ Assistant 실행
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # 최대 30초 대기
        for _ in range(30):
            status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if status.status == "completed":
                break
            time.sleep(1)

        # 응답 추출
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
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

        response_store[session_id] = answer

    except Exception as e:
        response_store[session_id] = f"오류 발생: {str(e)}"

@app.route("/ask", methods=["POST"])
def ask():
    try:
        message = request.json.get("message", "")
        if "thread_id" not in session:
            thread = openai.beta.threads.create()
            session["thread_id"] = thread.id

        thread_id = session["thread_id"]
        session_id = str(uuid.uuid4())

        # run 실행 중 여부 확인 (최신 run만 검사)
        try:
            runs = openai.beta.threads.runs.list(thread_id=thread_id, limit=1)
            if runs.data and runs.data[0].status in ["queued", "in_progress"]:
                return jsonify({"answer": "답변 생성 중입니다. 잠시 후 다시 시도해주세요."})
        except:
            pass

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

        # 최대 5초 동안 응답 대기
        for _ in range(5):
            status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if status.status == "completed":
                break
            time.sleep(1)

        if status.status == "completed":
            # 메시지 리스트 받아오기
            messages = openai.beta.threads.messages.list(thread_id=thread_id)
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

            return jsonify({"answer": answer})

        else:
            # 응답 준비 안 됨 → 백그라운드로 작업 넘김
            threading.Thread(target=fetch_assistant_response, args=(message, session_id, thread_id)).start()
            return jsonify({"answer": "잠시만 기다려주세요!", "session_id": session_id})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"answer": f"오류 발생: {str(e)}"}), 500

@app.route("/poll", methods=["GET"])
def poll():
    session_id = request.args.get("session_id")
    if session_id in response_store:
        answer = response_store.pop(session_id)  # 1회성 사용
        return jsonify({"answer_ready": True, "answer": answer})
    else:
        return jsonify({"answer_ready": False})

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js", mimetype='application/javascript')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
