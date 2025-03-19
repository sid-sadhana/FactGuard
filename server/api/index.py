from flask import Flask, request, jsonify
from flask_cors import CORS
import youtube_transcript_api
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Flask server!"})

@app.route('/api/guard-the-fact', methods=['POST'])
def guard_the_fact():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        video_id = url.split("v=")[-1].split("&")[0]
        transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry['text'] for entry in transcript])

        agent = Agent(
            model=OpenAIChat(id="gpt-4o", api_key=os.getenv("OPENAI_API_KEY")),
            description="""You're a fact-checking agent for data provided from videos' subtitles. Trust the sources more than the user's data. 
            Return a JSON response in the following format:
            {
                "fact_check": <your factual accuracy analysis here - don't refer to data as user provided data, refer to it as just "data" - MENTION INCORRECT DATA ONLY>,
                "hyper": [<add link sources here>],
                "images": [<add image link sources>],
                "score": <give your score out of 100 for the factual accuracy>
            }""",
            tools=[DuckDuckGoTools()],
            show_tool_calls=True,
            markdown=True
        )

        response = agent.run(text)
        json_data = response.content[response.content.find('```json') + 7: response.content.rfind('```')].strip()
        print(json_data)
        try:
            parsed_data = json.loads(json_data)
            return jsonify(parsed_data)
        except json.JSONDecodeError:
            return jsonify({"error": "Failed to parse JSON response", "raw_response": json_data}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
