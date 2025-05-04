from flask import Flask, request, jsonify
from flask_cors import CORS
import youtube_transcript_api
import os
import json
import time
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
import google.generativeai as genai
from tavily import TavilyClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from pinecone import Pinecone, ServerlessSpec
from nltk.tokenize import sent_tokenize
from agno.agent import Agent, RunResponse
from agno.models.google import Gemini

load_dotenv()

class FactCheckOutput(BaseModel):
    fact_check: str = Field(..., alias="fact_check", description="Provide reasoning and show only incorrect / factually inaccurate data")
    hyper: List[str] = Field(..., description="Include links for websites / blogs")
    images: List[str] = Field(..., description="Include links for images")
    score: int = Field(..., description="Factual Accuracy Score out of 100")

    class Config:
        populate_by_name = True

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not all([GOOGLE_API_KEY, TAVILY_API_KEY, PINECONE_API_KEY]):
    raise ValueError("Missing required environment variables")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-flash")
client = TavilyClient(api_key=TAVILY_API_KEY)

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

        json_mode_agent = Agent(
            model=Gemini(id="gemini-2.0-flash", api_key=GOOGLE_API_KEY),
            description="You are a content factual accuracy checker",
            response_model=FactCheckOutput,
            use_json_mode=True
        )

        json_mode_response: RunResponse = json_mode_agent.run(text)
        out = json_mode_response.content
        out_json = {
            "fact_check": out.fact_check,
            "hyper": out.hyper,
            "images": out.images,
            "score": out.score
        }
        return jsonify(out_json)
        # except json.JSONDecodeError:
        #     return jsonify({"error": "Invalid JSON response from model"}), 500

    except youtube_transcript_api.NoTranscriptFound:
        return jsonify({"error": "No transcript found for this video"}), 404
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/guard-the-fact-2', methods=['POST'])
def guard_the_fact_2():
    try:
        print("\n=== Starting Fact Check Process ===")
        data = request.json
        print("[1/8] Received request data:", data)
        
        if not data or "url" not in data:
            print("! Error: No URL provided")
            return jsonify({"error": "No URL provided"}), 400

        url = data["url"]
        print("[2/8] Processing URL:", url)
        
        try:
            video_id = url.split("v=")[-1].split("&")[0]
            print("  Extracted Video ID:", video_id)
        except Exception as e:
            print("! Error extracting video ID:", str(e))
            return jsonify({"error": "Invalid YouTube URL"}), 400

        print("[3/8] Fetching transcript...")
        try:
            transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
            full_text = " ".join([entry['text'] for entry in transcript])
            print(f"  Retrieved transcript ({len(full_text)} characters)")
            print(f"  Sample text: {full_text}...")
        except Exception as e:
            print("! Transcript error:", str(e))
            return jsonify({"error": "Transcript unavailable"}), 500

        print("[4/8] Generating structured points with Gemini...")
        try:
            response = model.generate_content(
                f"""Convert transcript into independent factual statements separated by @@@:
                {full_text}
                Respond ONLY with @@@-separated statements"""
            )
            points = [p.strip() for p in response.text.split("@@@")]
            points=points[:5]
            print(f"  Generated {len(points)} points")
            print("  Sample points:", points)
        except Exception as e:
            print("! Gemini point generation failed:", str(e))
            return jsonify({"error": "Analysis failed"}), 500

        print("[5/8] Searching Tavily and processing results...")
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=250,
        )
        
        pc = Pinecone(api_key=PINECONE_API_KEY)
        index_name = "factguard-index"
        print(f"  Using Pinecone index: {index_name}")
        
        links = ""
        for i, point in enumerate(points):
            print(f"  Processing point {i+1}/{len(points)}: {point[:50]}...")
            try:
                search_result = client.search(
                    query=point,
                    search_depth="basic",
                    max_results=1,
                    include_domains=[
                        "bbc.com", "en.wikipedia.org", "reuters.com",
                        "apnews.com", "theguardian.com", "nytimes.com"
                    ]
                )
                print(f"    Found {len(search_result.get('results', []))} results")
                
                for result in search_result.get("results", []):
                    url = result.get("url")
                    if url:
                        try:
                            print(f"    Loading URL: {url[:60]}...")
                            loader = WebBaseLoader(url)
                            page = loader.load()
                            if page:
                                links += page[0].page_content + "\n"
                        except Exception as e:
                            print(f"    ! Error loading page: {str(e)}")
                time.sleep(1)
                print("    Rate limit wait complete")
            except Exception as e:
                print(f"! Error processing point {i+1}: {str(e)}")

        print("[6/8] Processing documents for Pinecone...")
        try:
            texts = text_splitter.create_documents([links])
            print(f"  Created {len(texts)} text chunks")
            
            if index_name not in pc.list_indexes().names():
                print("  Creating new Pinecone index")
                pc.create_index(
                    name=index_name,
                    dimension=768,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
            
            index = pc.Index(index_name)
            print("  Upserting vectors...")
            for idx, doc in enumerate(texts):
                doc_result = embeddings.embed_documents([doc.page_content])
                index.upsert(vectors=[{
                    "id": str(idx),
                    "metadata": {"text": doc.page_content},
                    "values": doc_result[0]
                }], namespace="ns1")
            print(f"  Inserted {len(texts)} vectors")
        except Exception as e:
            print("! Vector processing failed:", str(e))
            return jsonify({"error": "Data processing failed"}), 500

        print("[7/8] Verifying points...")
        out=""
        for i in points:
            time.sleep(3)
            query_result = embeddings.embed_query(i)
            results = index.query(
            namespace="ns1",
            vector=query_result,
            top_k=1,
            include_metadata=True
            )
            print(i)
            print(results["matches"][0]["metadata"]["text"])
            print()
            response = model.generate_content(
            f"""You are a fact-checking agent. Given the query: "{i}" and the factual data: "{results['matches'][0]['metadata']['text']}", identify any inaccuracies or false claims present in the query. 
        Rely entirely on the factual data as the trusted source of truth. Only flag statements that clearly contradict the factual data. 
        List the inaccuracies clearly and objectively."""
        , 
            stream=False,
            generation_config={"response_mime_type":"text/plain"}
            )
            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    out+=chunk.text

        print("[8/8] Process complete")
        pc.delete_index(name="factguard-index")
        return jsonify({
            "fact_check": out,
            "hyper":[],
            "images":[],
            "score": 100
        })

    except Exception as e:
        print("!!! Critical error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)