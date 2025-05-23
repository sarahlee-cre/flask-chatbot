import os
import time
import openai
from flask import Flask, request, jsonify, render_template_string, send_from_directory, session
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "hubi-temp-secret")

@app.route("/install")
def install():
    session.clear()
    html_template = """
    <!DOCTYPE html>
    <html lang=\"ko\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <title>HUFS 비서, HUBEE</title>
        <link rel=\"manifest\" href=\"/static/manifest.json\">
        <link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap\">
        <meta name=\"theme-color\" content=\"#ffffff\">
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
                chatBox.innerHTML += `<div class='bubble user'>🙋‍♀️ ${userInput}</div>`;
                inputEl.value = "";
                chatBox.scrollTop = chatBox.scrollHeight;

                const res = await fetch("/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: userInput })
                });

                const data = await res.json();
                chatBox.innerHTML += `<div class='bubble bot'><img class='bubble-icon' src='/static/icons/icon192.png' /> ${data.answer}</div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            function setExample() {
                document.getElementById("userInput").value = "학사 일정 알려줘";
            }
        </script>
        <style>
            body {
                font-family: 'Noto Sans KR', sans-serif;
                margin: 0;
                padding: 0;
                background: #eaf6ff;
                display: flex;
                flex-direction: column;
                height: 100vh;
            }
            header {
                background: #fff;
                padding: 1rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid #ddd;
            }
            .logo {
                height: 40px;
                margin-right: 0.5rem;
            }
            .title {
                font-weight: bold;
                font-size: 1.2rem;
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
                background: #003b6f;
                color: #fff;
            }
            .bot {
                align-self: flex-start;
                background: #fff;
                border: 1px solid #ddd;
                color: #333;
            }
            .bubble-icon {
                height: 20px;
                vertical-align: middle;
                margin-right: 0.3rem;
            }
            #input-area {
                display: flex;
                padding: 0.75rem;
                background: #fff;
                border-top: 1px solid #ccc;
                align-items: center;
            }
            .example-btn, .file-icon, .send-btn {
                background: none;
                border: none;
                cursor: pointer;
                font-size: 1rem;
                margin: 0 0.5rem;
            }
            #userInput {
                flex: 1;
                padding: 0.6rem;
                border: 1px solid #ccc;
                border-radius: 20px;
                outline: none;
            }
            .send-btn {
                background-color: #0066cc;
                color: white;
                padding: 0.6rem 1rem;
                border-radius: 20px;
            }
        </style>
    </head>
    <body>
        <header>
            <div style="display: flex; align-items: center;">
                <img src="/static/icons/icon192.png" class="logo" alt="HUBEE 로고" />
                <div class="title">HUFS 비서, HUBEE</div>
            </div>
            <button class="search-icon">🔍</button>
        </header>
        <div id="chat-box">
            <div class="bubble bot"><img class='bubble-icon' src='/static/icons/icon192.png' /> 안녕하세요! 저는 한국외대 챗봇 후비입니다. 무엇을 도와드릴까요? 😊</div>
        </div>
        <div id="input-area">
            <button onclick="setExample()" class="example-btn">질문예시</button>
            <label for="fileUpload" class="file-icon">📎</label>
            <input type="file" id="fileUpload" hidden />
            <input id="userInput" type="text" placeholder="메시지를 입력하세요..." onkeydown="if(event.key==='Enter') sendToGPT()" />
            <button onclick="sendToGPT()" class="send-btn">전송</button>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)

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

        for _ in range(30):
            status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if status.status == "completed":
                break
            time.sleep(1)

        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        answer = ""
        for msg in reversed(messages.data):
            if msg.role == "assistant":
                for part in msg.content:
                    if part.type == "text":
                        answer = part.text.value.strip()
                        break
                if answer:
                    break

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"answer": f"오류 발생: {str(e)}"})

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run()
