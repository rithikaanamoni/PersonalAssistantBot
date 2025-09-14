import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import wikipedia
from groq import Groq
import re
from datetime import datetime
import pytz

# --------------------- LOAD ENV ---------------------
load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")  # TheSportsDB free key: 123

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Initialize Flask
app = Flask(__name__)
app.secret_key = "your_secret_key"

# System prompt for AI
system_prompt = """
You are a helpful AI assistant.
- Answer questions clearly.
- Solve math problems.
- Write code if user asks.
- Be friendly and concise.
"""

# Conversation memory
conversation_history = []

# --------------------- API FUNCTIONS ---------------------

# Weather for any city
def get_weather(user_input):
    try:
        # Extract city name after 'weather' or 'whether'
        match = re.search(r'(?:weather|whether)\s*(?:in\s+)?([a-zA-Z\s]+)', user_input, re.I)
        city = match.group(1).strip() if match else "Hyderabad"

        # API call
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
        res = requests.get(url).json()
        if int(res.get("cod", 0)) != 200:
            return f"❌ Couldn't fetch weather for {city}. API message: {res.get('message','Unknown error')}"

        temp = res["main"]["temp"]
        desc = res["weather"][0]["description"]
        return f"🌤️ Weather in {city}: {temp}°C, {desc}"

    except Exception as e:
        return f"⚠️ Error fetching weather: {str(e)}"

# News
def get_news():
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}"
        res = requests.get(url).json()
        if res.get("status") != "ok":
            return f"❌ Couldn't fetch news. API message: {res.get('message','Unknown error')}"
        headlines = [a["title"] for a in res["articles"][:5]]
        return "📰 Top News:\n" + "\n".join([f"- {h}" for h in headlines])
    except Exception as e:
        return f"⚠️ Error fetching news: {str(e)}"

# Sports
def get_sports():
    try:
        url = f"https://www.thesportsdb.com/api/v1/json/{SPORTS_API_KEY}/all_sports.php"
        res = requests.get(url).json()
        sports_list = [s["strSport"] for s in res.get("sports", [])[:5]]
        return "🏅 Popular Sports:\n" + "\n".join([f"- {s}" for s in sports_list])
    except Exception as e:
        return f"⚠️ Error fetching sports: {str(e)}"

# Wikipedia
def get_wiki(query):
    try:
        summary = wikipedia.summary(query, sentences=2)
        return f"📖 {summary}"
    except Exception as e:
        return f"❌ No info found: {str(e)}"

# --------------------- CHATBOT FUNCTION ---------------------
def chatbot_response(user_input):
    user_lower = user_input.lower()

    # WEATHER detection
    if "weather" in user_lower or "whether" in user_lower:
        return get_weather(user_input)

    # NEWS detection
    elif "news" in user_lower:
        return get_news()

    # SPORTS detection
    elif "sports" in user_lower:
        return get_sports()

    # DATE/TIME detection
    elif "date" in user_lower or "time" in user_lower:
        try:
            india_tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(india_tz)
            if "date" in user_lower:
                return f"📅 Today's date in India: {now.strftime('%B %d, %Y')}"
            elif "time" in user_lower:
                return f"⏰ Current time in India: {now.strftime('%H:%M:%S')}"
        except Exception as e:
            return f"⚠️ Error fetching time/date: {str(e)}"

    # WIKIPEDIA detection
    elif user_lower.startswith("who is") or user_lower.startswith("what is"):
        return get_wiki(user_input)

    # Otherwise → Groq AI fallback
    conversation_history.append({"role": "user", "content": user_input})
    try:
        messages = [{"role": "system", "content": system_prompt}] + conversation_history
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages
        )
        reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# --------------------- FLASK ROUTES ---------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "")
    response = chatbot_response(user_input)
    return jsonify({"response": response})

# --------------------- RUN APP ---------------------
if __name__ == "__main__":
    app.run(debug=True)
