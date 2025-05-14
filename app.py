from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Flask 서버 실행 중입니다!"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": "✅ 서버가 정상적으로 응답하고 있어요!"
                        }
                    }
                ]
            }
        })
    except Exception as e:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": f"❌ 오류 발생: {str(e)}"
                        }
                    }
                ]
            }
        })

if __name__ == "__main__":
    app.run()
