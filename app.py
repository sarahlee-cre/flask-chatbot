import os
import time
import openai
from flask import Flask, request, jsonify, render_template_string, send_from_directory, session
from dotenv import load_dotenv

# 환경변수 불러오기
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "hubi-temp-secret")

# 📄 메인 페이지 (채팅 + PWA)
@app.route("/install")
def install():
    html_template = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>후비 GPT 챗봇</title>
        <link rel="manifest" href="/static/manifest.json" />
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap" />
        <meta name="theme-color" content="#ffffff" />
        <script>
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                    navigator.serviceWorker.register('/static/sw.js');
                });
            }

            async function sendToGPT() {
                const inputEl = document.getElementById("userInput");
                const userInput = inputEl.value.trim();
                if (!userInput) return;

                const chatBox = document.getElementById("chat-box");
                chatBox.innerHTML += `<div class="bubble user">🙋‍♀️ ${userInput}</div>`;
                inputEl.value = "";
                chatBox.scrollTop = chatBox.scrollHeight;

                const res = await fetch("/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: userInput })
                });

                const data = await res.json();
                chatBox.innerHTML += `<div class="bubble bot">🤖 ${data.answer}</div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        </script>
        <style>
            body {
                font-family: 'Noto Sans KR', sans-serif;
                margin: 0;
                padding: 0;
                background: #f2f2f2;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            h1 {
                text-align: center;
                padding: 1rem;
                background: #ffffff;
                margin: 0;
                font-size: 1.3rem;
                border-bottom: 1px solid #ddd;
            }
            #chat-box {
                flex: 1;
                overflow-y: auto;
                padding: 1rem;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            .bubble {
                padding: 0.75rem 1rem;
                border-radius: 20px;
                max-width: 75%;
                word-wrap: break-word;
                white-space: pre-wrap;
                font-size: 0.95rem;
                line-height: 1.5;
            }
            .user {
                align-self: flex-end;
                background: #d0f0ff;
                color: #000;
            }
            .bot {
                align-self: flex-start;
                background: #fff;
                border: 1px solid #ddd;
                color: #333;
            }
            #input-area {
                display: flex;
                padding: 0.75rem;
                background: #fff;
                border-top: 1px solid #ccc;
            }
            #userInput {
                flex: 1;
                padding: 0.6rem;
                border: 1px solid #ccc;
                border-radius: 20px;
                outline: none;
            }
            button {
                margin-left: 0.5rem;
                padding: 0.6rem 1rem;
                border: none;
                border-radius: 20px;
                background-color: #0066cc;
                color: white;
                cursor: pointer;
            }
            button:hover {
                background-color: #004999;
            }
        </style>
    </head>
    <body>
        <h1>🤖 HUBI GPT 챗봇</h1>
        <div id="chat-box">
            <div class="bubble bot">안녕하세요! 저는 한국외대 챗봇 후비입니다. 무엇을 도와드릴까요? 😊</div>
        </div>
        <div id="input-area">
            <input id="userInput" type="text" placeholder="메시지를 입력하세요..." onkeydown="if(event.key==='Enter') sendToGPT()" />
            <button onclick="sendToGPT()">전송</button>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)

# 💬 GPT 응답 API
@app.route("/ask", methods=["POST"])
def ask():
    try:
        message = request.json.get("message", "")

        if "thread_id" not in session:
            thread = openai.beta.threads.create()
            session["thread_id"] = thread.id
        thread_id = session["thread_id"]

        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message
        )

        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # 최대 30초까지 대기
        for _ in range(30):
            status = openai.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
            if status.status == "completed":
                break
            time.sleep(1)

        # 🔁 모든 assistant 메시지 이어붙이기
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        answer = ""
        for msg in reversed(messages.data):  # 최신부터 확인
            if msg.role == "assistant":
                for part in msg.content:
                    if part.type == "text":
                        answer += part.text.value.strip() + "\n"

        return jsonify({"answer": answer.strip()})

    except Exception as e:
        return jsonify({"answer": f"오류 발생: {str(e)}"})

# 🌐 정적 파일 제공
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# 🖥 실행
if __name__ == "__main__":
    app.run()
