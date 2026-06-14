from db import (
    init_db,
    save_learning_content,
    get_latest_learning_content,
    get_user,
    update_user_xp,
    save_quiz_result,
    get_latest_quiz_result
)
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
CORS(app)
study_groups_data = [
    {
        "group_id": 1,
        "group_name": "Bio Boosters",
        "focus_topic": "Respiration",
        "members": ["Aarav", "Meera", "Diya"],
        "level": "Beginner",
        "description": "A group focused on improving biology basics and respiration concepts."
    },
    {
        "group_id": 2,
        "group_name": "Genetics Warriors",
        "focus_topic": "Genetics",
        "members": ["Rohan", "Anika", "Dev"],
        "level": "Intermediate",
        "description": "A study group for solving genetics-based questions and doubts."
    },
    {
        "group_id": 3,
        "group_name": "Photosynthesis Squad",
        "focus_topic": "Photosynthesis",
        "members": ["Nina", "Arjun", "Sara"],
        "level": "Beginner",
        "description": "A group for mastering photosynthesis through quizzes and flashcards."
    },
    {
        "group_id": 4,
        "group_name": "Science Quest Team",
        "focus_topic": "General Science",
        "members": ["Isha", "Kabir", "Vivek"],
        "level": "Mixed",
        "description": "A general revision group for science learners."
    }
]
try:
    init_db()
    print("Database initialized successfully.")
except Exception as e:
    print("Database initialization skipped or failed:", e)

def generate_learning_content_with_gemini(extracted_text):
    prompt = f"""
You are an AI study assistant for a gamified learning platform called LevelUp.

From the student notes below, generate study content.

Return ONLY valid JSON.
Do not include markdown.
Do not include explanation outside JSON.

JSON format:
{{
  "subject": "Subject name",
  "topics": ["Topic 1", "Topic 2", "Topic 3"],
  "summary": "Short summary of the notes in 2-3 lines.",
  "quiz": [
    {{
      "id": 1,
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Correct option text",
      "topic": "Related topic",
      "difficulty": "Easy"
    }}
  ],
  "flashcards": [
    {{
      "front": "Question or term",
      "back": "Answer or explanation",
      "topic": "Related topic"
    }}
  ]
}}

Rules:
- Generate exactly 5 quiz questions.
- Each quiz question must have exactly 4 options.
- Generate exactly 5 flashcards.
- Keep language simple for students.
- Make sure the answer exactly matches one of the options.

Student notes:
{extracted_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    ai_text = response.text.strip()

    if ai_text.startswith("```json"):
        ai_text = ai_text.replace("```json", "").replace("```", "").strip()
    elif ai_text.startswith("```"):
        ai_text = ai_text.replace("```", "").strip()

    return json.loads(ai_text)

@app.route("/")
def home():
    return jsonify({"message": "LevelUp backend is running!"})


@app.route("/api/process-notes", methods=["POST"])
def process_notes():
    data = request.get_json()
    extracted_text = data.get("text", "") or data.get("ocr_text", "")

    if not extracted_text:
        return jsonify({"error": "No text provided"}), 400

    try:
        response = generate_learning_content_with_gemini(extracted_text)

        try:
            content_id = save_learning_content(response)
            response["content_id"] = content_id
        except Exception as db_error:
            print("DB save learning content error:", db_error)

        return jsonify(response)

    except Exception as e:
        print("Gemini error:", e)

        fallback_response = {
            "subject": "Biology",
            "topics": ["Photosynthesis", "Respiration", "Genetics"],
            "summary": "AI generation failed, so this fallback demo content is shown.",
            "quiz": [
                {
                    "id": 1,
                    "question": "What is the main purpose of photosynthesis?",
                    "options": [
                        "To produce glucose",
                        "To absorb nitrogen",
                        "To release minerals",
                        "To create proteins"
                    ],
                    "answer": "To produce glucose",
                    "topic": "Photosynthesis",
                    "difficulty": "Easy"
                }
            ],
            "flashcards": [
                {
                    "front": "What is photosynthesis?",
                    "back": "Photosynthesis is the process by which green plants make food using sunlight, carbon dioxide, and water.",
                    "topic": "Photosynthesis"
                }
            ]
        }

        try:
            content_id = save_learning_content(fallback_response)
            fallback_response["content_id"] = content_id
        except Exception as db_error:
            print("DB save fallback error:", db_error)

        return jsonify(fallback_response)

@app.route("/api/submit-quiz", methods=["POST"])
def submit_quiz():
    data = request.get_json()
    answers = data.get("answers", [])

    score = 0
    weak_topics = []

    for answer in answers:
        if answer.get("selected") == answer.get("correct"):
            score += 1
        else:
            weak_topics.append(answer.get("topic"))

    weak_topics = list(set(weak_topics))

    try:
        user = get_user()
        current_xp = user["xp"] if user else 240
    except Exception as db_error:
        print("DB user fetch skipped:", db_error)
        current_xp = 240

    xp_earned = score * 10
    total_xp = current_xp + xp_earned
    level = (total_xp // 100) + 1
    next_level_xp = level * 100

    recommended_groups = []

    for group in study_groups_data:
        if group["focus_topic"] in weak_topics:
            recommended_groups.append({
                "group_id": group["group_id"],
                "group_name": group["group_name"],
                "focus_topic": group["focus_topic"],
                "members_count": len(group["members"]),
                "level": group["level"],
                "description": group.get("description", ""),
                "match_reason": f"Recommended because you need improvement in {group['focus_topic']}."
            })

    if not recommended_groups:
        recommended_groups.append({
            "group_id": 4,
            "group_name": "Science Quest Team",
            "focus_topic": "General Science",
            "members_count": 3,
            "level": "Mixed",
            "description": "A general revision group for science learners.",
            "match_reason": "Recommended because it matches your general learning activity."
        })

    result = {
        "score": score,
        "total": len(answers),
        "xp_earned": xp_earned,
        "total_xp": total_xp,
        "level": level,
        "next_level_xp": next_level_xp,
        "weak_topics": weak_topics,
        "recommended_groups": recommended_groups,
        "message": "Great effort! Keep practicing your weak topics."
    }

    try:
        update_user_xp(total_xp, level)
        result_id = save_quiz_result(result)
        result["result_id"] = result_id
    except Exception as db_error:
        print("DB quiz result save error:", db_error)

    return jsonify(result)

@app.route("/api/user-progress", methods=["GET"])
def user_progress():
    return jsonify({
        "level": 3,
        "xp": 240,
        "streak": 5,
        "badges": ["Quick Learner", "Quiz Starter"],
        "strong_topics": ["Photosynthesis"],
        "weak_topics": ["Respiration"]
    })


@app.route("/api/study-groups", methods=["POST"])
def study_groups():
    data = request.get_json()

    weak_topics = data.get("weak_topics", [])

    recommended_groups = []

    for group in study_groups_data:
        if group["focus_topic"] in weak_topics:
            recommended_groups.append({
                "group_id": group["group_id"],
                "group_name": group["group_name"],
                "focus_topic": group["focus_topic"],
                "members_count": len(group["members"]),
                "level": group["level"],
                "description": group["description"],
                "match_reason": f"Recommended because you need improvement in {group['focus_topic']}."
            })

    if not recommended_groups:
        recommended_groups.append({
            "group_id": 4,
            "group_name": "Science Quest Team",
            "focus_topic": "General Science",
            "members_count": 3,
            "level": "Mixed",
            "description": "A general revision group for science learners.",
            "match_reason": "Recommended because it matches your general learning activity."
        })

    return jsonify({
        "weak_topics": weak_topics,
        "recommended_groups": recommended_groups
    })

@app.route("/api/latest-learning-content", methods=["GET"])
def latest_learning_content():
    try:
        content = get_latest_learning_content()

        if not content:
            return jsonify({"error": "No learning content found"}), 404

        return jsonify({
            "id": content["id"],
            "subject": content["subject"],
            "summary": content["summary"],
            "topics": content["topics"],
            "quiz": content["quiz"],
            "flashcards": content["flashcards"],
            "created_at": str(content["created_at"])
        })

    except Exception as e:
        print("Latest learning content error:", e)
        return jsonify({"error": "Could not fetch latest learning content"}), 500


@app.route("/api/latest-quiz-result", methods=["GET"])
def latest_quiz_result():
    try:
        result = get_latest_quiz_result()

        if not result:
            return jsonify({"error": "No quiz result found"}), 404

        return jsonify({
            "id": result["id"],
            "score": result["score"],
            "total": result["total"],
            "xp_earned": result["xp_earned"],
            "total_xp": result["total_xp"],
            "level": result["level"],
            "next_level_xp": result["next_level_xp"],
            "weak_topics": result["weak_topics"],
            "recommended_groups": result["recommended_groups"],
            "created_at": str(result["created_at"])
        })

    except Exception as e:
        print("Latest quiz result error:", e)
        return jsonify({"error": "Could not fetch latest quiz result"}), 500



if __name__ == "__main__":
    app.run(debug=True)