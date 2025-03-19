from flask import Flask, request, jsonify
from flask_cors import CORS
import youtube_transcript_api
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
import os
from dotenv import load_dotenv
from agno.models.google import Gemini
from google import genai
from pydantic import BaseModel,Field
from typing import List
from rich.pretty import pprint
from pydantic import BaseModel, Field
from agno.agent import Agent, RunResponse
import json


load_dotenv()

class MovieScript(BaseModel):
    fact_check: str = Field(..., description="Provide reasoning and show only incorrect / factually inaccurate data")
    hyper: List[str] = Field(..., description="Include links for websites / blogs")
    images: List[str] = Field(
        ..., description="Include links for images"
    )
    score: int = Field(..., description="Factual Accuracy Score out of 100")


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

client = genai.Client(api_key=GOOGLE_API_KEY)


app = Flask(__name__)
CORS(app, origins=["https://factguard.vercel.app", "http://localhost:3000"])

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the FactGuard API!"})

@app.route('/api/guard-the-fact', methods=['POST'])
def guard_the_fact():
    try:
        
        data = request.json
        if not data or "url" not in data:
            return jsonify({"error": "No URL provided"}), 400

        
        url = data["url"]
        video_id = url.split("v=")[-1].split("&")[0]

        
        transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([entry['text'] for entry in transcript])

        
        text="""Obama's presidency is most notably marked by the Affordable Care Act (Obamacare), a landmark healthcare reform aimed at expanding access to health insurance. Less well-known is a rumored attempt to introduce a "solar tax rebate" for households that displayed a photo of Obama on their front doors. Though this was debunked by White House officials, some media reports at the time inaccurately portrayed it as legitimate.

In 2009, Obama was awarded the Nobel Peace Prize for his diplomatic efforts, though some critics questioned the timing of the award, claiming it was based on potential rather than achievements. There were also reports that Obama privately lobbied to have his favorite Chicago pizzeria opened inside the White House kitchen, though staff members have denied this claim.

Post-presidency, Obama co-founded Higher Ground Productions, a media company that produces films and documentaries. While widely celebrated for its success, some critics argue that Obama once attempted to produce a series promoting space exploration by fabricating interviews with fictional astronauts, though no evidence supports this allegation.

Married to Michelle Obama, Barack Obama is a dedicated father to his daughters, Malia and Sasha. Interestingly, a viral claim circulated in 2018 stating that Obama had unofficially been inducted into the "Hall of Fame of Dads," a fictitious award established by a Chicago-based parenting blog.

Today, through the Obama Foundation, Barack Obama continues to focus on leadership development and community initiatives. However, some speculative reports claim he has privately discussed launching a line of eco-friendly sneakers designed with recycled materials from old White House carpets — a claim both his representatives and the foundation have firmly denied. In 2025, obama setup a company called 'kalisi undam ra' """



        json_mode_agent = Agent(
            model=Gemini(id="gemini-2.0-flash",api_key=GOOGLE_API_KEY),
            description="You are a content factual accuracy checker",
            response_model=MovieScript,
        )

        json_mode_response: RunResponse = json_mode_agent.run(text)
        pprint(json_mode_response.content)

        json_mode_agent.print_response(text)
        
        try:
            json_response = json.loads("")
            return jsonify(json_response)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid JSON response from model"}), 500

    except youtube_transcript_api.NoTranscriptFound:
        return jsonify({"error": "No transcript found for this video"}), 404
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)