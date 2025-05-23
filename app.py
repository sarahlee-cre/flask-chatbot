import os
import time
import openai
from flask import Flask, request, jsonify, render_template_string, send_from_directory, session
from dotenv import load_dotenv

# .env 파일의 환경변수 불러오기
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__, static_folder="static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "hubi-temp-secret")  # 세션 유지용 시크릿 키

@app.route("/install")
def install():
    session.clear()
    html_template = """
    <!DOCTYPE html>
    <html lang=\"ko\">
    <head>
        <meta charset=\"UTF-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
        <title>후비 HUBI</title>
        <link rel=\"manifest\" href=\"/static/manifest.json\" />
        <link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap\" />
        <meta name=\"theme-color\" content=\"#ffffff\" />
        <script>
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                    navigator.serviceWorker.register('/static/sw.js');
                });
            }

            let history = [];

            async function sendToGPT() {
                const inputEl = document.getElementById("userInput");
                const userInput = inputEl.value.trim();
                if (!userInput) return;

                const chatBox = document.getElementById("chat-box");
                chatBox.innerHTML += `<div class='bubble user'>🙋‍♀️ ${userInput}</div>`;
                inputEl.value = "";
                chatBox.scrollTop = chatBox.scrollHeight;
                history.push({ role: 'user', content: userInput });

                const res = await fetch("/ask", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ message: userInput })
                });

                const data = await res.json();
                chatBox.innerHTML += `<div class='bubble bot'><img class='bot-icon' src='/static/icons/icon3.png'> ${data.answer.replace(/\\n/g, '<br>')}</div>`;
                chatBox.scrollTop = chatBox.scrollHeight;
                history.push({ role: 'bot', content: data.answer });
            }

            function clearChat() {
                document.getElementById("chat-box").innerHTML = "";
                history = [];
            }

            function viewHistory() {
                alert(history.map(h => `${h.role === 'user' ? '🙋‍♀️' : '🤖'} ${h.content}`).join('\n\n'));
            }

            document.addEventListener("DOMContentLoaded", function () {
                const toggleBtn = document.getElementById("toggleExamples");
                const list = document.getElementById("exampleList");

                toggleBtn.addEventListener("click", () => {
                    list.style.display = list.style.display === "none" ? "block" : "none";
                });

                document.querySelectorAll(".example-question").forEach(btn => {
                    btn.addEventListener("click", () => {
                        const text = btn.innerText;
                        document.getElementById("userInput").value = text;
                        list.style.display = "none";
                        sendToGPT();
                    });
                });
            });
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
                background: #ffffff;
                padding: 1rem 2rem;
                display: flex;
                align-items: center;
                justify-content: center;
                border-bottom: 1px solid #ddd;
                gap: 0.5rem;
                position: relative;
            }
            .logo {
                height: 40px;
            }
            .title {
                font-weight: bold;
                font-size: 1.3rem;
            }
            .search-btn {
                border: none;
                background: none;
                cursor: pointer;
                font-size: 1.2rem;
                position: absolute;
                right: 2rem;
            }
            .info-icon {
                position: absolute;
                left: 1rem;
                top: 50%;
                transform: translateY(-50%);
            }
            #chat-box {
                flex: 1;
                overflow-y: auto;
                padding: 1rem 2rem;
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
                background: #ffffff;
                border: 1px solid #ddd;
                color: #333;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .bot-icon {
                height: 28px;
                width: 28px;
            }
            #input-area {
                display: flex;
                padding: 0.75rem;
                background: #fff;
                border-top: 1px solid #ccc;
                gap: 0.5rem;
                align-items: center;
            }
            #userInput {
                flex: 1;
                padding: 0.6rem;
                border: 1px solid #ccc;
                border-radius: 20px;
                outline: none;
            }
            button {
                padding: 0;
                border: none;
                border-radius: 50%;
                background-color: transparent;
                cursor: pointer;
            }
            #toggleExamples {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 46px;
                height: 46px;
                font-size: 24px;
                border-radius: 50%;
                background-color: #e7f0ff;
                border: 2px solid #a5cfff;
            }
            #send-btn {
                width: 35px;
                height: 35px;
                background-color: #007bff;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            #end-btn {
                width: 35px;
                height: 35px;
                background-color: #ff0000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .example-question {
                display: block;
                width: 100%;
                text-align: left;
                padding: 6px 12px;
                background-color: #f9f9f9;
                border: none;
                font-size: 0.9rem;
                cursor: pointer;
            }
            .example-question:hover {
                background-color: #eef6ff;
            }
        </style>
    </head>
    <body>
        <!-- 나머지 HTML 동일 -->
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
