from flask import Flask, render_template, request
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    """
    Renders the homepage.
    """
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """
    A simple API endpoint to check the server status.
    """
    return {"status": "ok", "service": "Project Alpha"}

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Handles chat prompts by sending them to the Gemini API.
    """
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return {"status": "error", "message": "API key is not configured."}, 500

    prompt = request.json.get('prompt')
    if not prompt:
        return {"status": "error", "message": "No prompt provided."}, 400

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return {"status": "success", "response": response.text}
    except Exception as e:
        # This will catch errors from an invalid API key, network issues, etc.
        print(f"An error occurred while contacting the Gemini API: {e}")
        return {"status": "error", "message": "An error occurred while processing your request."}, 503

if __name__ == '__main__':
    app.run(debug=True)
