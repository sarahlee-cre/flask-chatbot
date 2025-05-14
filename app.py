import os
import threading
import openai
import time
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

app = Flask(__name__, static_folder="static")

@app.route("/install")
def install():
    html_template = """
    <!DOCTYPE html>
    <html lang=\"ko\">
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
        <meta name=\"theme-color\" content=\"#ffffff\">
        <link rel=\"manifest\" href=\"/static/manifest.json\">
        <link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap\">
        <title>후비 GPT 챗봇</title>
        <script>
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', () => {
                    navigator.serviceWorker.register('/static/sw.js');
                });
            }
            async function sendToGPT() {
                const input = document.getElementById("userInput").value;
                document.getElementById("response").innerText = "⏳ 응답 생성 중...";

                const res = await fetch("/ask", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ message: input })
                });

                const data = await res.json();
                document.getElementById("response").innerText = "🤖 " + data.answer;
            }
        </script>
        <style>
            body { font-family: 'Noto Sans KR', sans-serif; text-align: center; padding: 2rem; background-color: #f4f4f4; }
            h1 { margin-bottom: 1rem; }
            p { font-size: 1.2rem; color: #333; }
            input { padding: 0.5rem; width: 70%; max-width: 400px; margin-top: 2rem; }
            button { padding: 0.5rem 1rem; margin-left: 0.5rem; }
            #response { margin-top: 2rem; font-size: 1.1rem; color: #111; white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <h1>🤖 HUBI GPT 챗봇</h1>
        <p>PWA 설치가 가능한 챗봇입니다.<br>홈 화면에 추가하여 앱처럼 사용할 수 있어요!</p>
        <input id=\"userInput\" placeholder=\"질문을 입력하세요\">
        <button onclick=\"sendToGPT()\">보내기</button>
        <div id=\"response\">🤖 답변이 여기에 표시됩니다</div>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route("/ask", methods=["POST"])
def ask():
    try:
        message = request.json["message"]

        thread = openai.beta.threads.create()
        openai.beta.threads.messages.create(thread_id=thread.id, role="user", content=message)
        run = openai.beta.threads.runs.create(thread_id=thread.id, assistant_id=ASSISTANT_ID)

        for _ in range(10):
            status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if status.status == "completed":
                break
            time.sleep(1)

        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        answer = messages.data[0].content[0].text.value

        return jsonify({"answer": answer})

    except Exception as e:
        return jsonify({"answer": f"오류 발생: {str(e)}"})

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    app.run()