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
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from google import genai

GEMINI_MODEL = "gemini-2.5-flash"

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


try:
    from image_processing.ocr_service import QuizTextExtractorService
    ocr_engine = QuizTextExtractorService()
    print("OCR engine loaded successfully.")
except Exception as e:
    print("OCR engine skipped:", e)
    ocr_engine = None

app = Flask(__name__)
CORS(app)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
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


def generate_learning_content_with_gemini(extracted_text, difficulty="Medium", quiz_type="MCQ Arena",
                                              question_count="5"):
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
- Generate exactly {question_count} quiz questions.
- Difficulty level should be {difficulty}.
- Quiz mode should be {quiz_type}.
- If quiz mode is True / False Match, generate true/false style questions with options ["True", "False"].
- If quiz mode is MCQ Arena, each quiz question must have exactly 4 options.
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

def generate_local_doubt_fallback(question, context):
    question_lower = question.lower()
    context_lower = context.lower()

    important_lines = []

    for line in context.splitlines():
        clean_line = line.strip()

        if not clean_line:
            continue

        line_lower = clean_line.lower()

        for word in question_lower.split():
            if len(word) > 4 and word in line_lower:
                important_lines.append(clean_line)
                break

    if important_lines:
        matched_context = " ".join(important_lines[:5])

        return f"""
Based on your uploaded notes, this doubt is related to:

{matched_context}

Simple explanation:
The topic you asked about appears in your latest learning material. Focus on its definition, how it works, and where it is used. For exam revision, try to remember the key property, one example, and one application.

Suggested next step:
Open the Flashcards page and revise the cards related to this topic.
"""

    if "thermistor" in question_lower:
        return """
A thermistor is a temperature-sensitive resistor.

Its resistance changes when temperature changes.

Key point:
Most thermistors have a negative temperature coefficient, meaning when temperature increases, resistance decreases.

Simple example:
A thermistor can be used in temperature sensors, digital thermometers, fire alarms, and electronic circuits that need temperature monitoring.
"""

    return """
I could not find an exact matching line from your uploaded notes, but here is how to approach this doubt:

1. Identify the definition of the concept.
2. Find the main working principle.
3. Connect it to one real-world example.
4. Revise the related flashcard or weak topic from your latest quiz.

Try asking with a specific keyword from your notes for a more focused explanation.
"""

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

    xp_earned = score * 50
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
        for index, topic in enumerate(weak_topics):
            recommended_groups.append({
                "group_id": 100 + index,
                "group_name": f"{topic} Study Squad",
                "focus_topic": topic,
                "members_count": 3 + index,
                "level": "Adaptive",
                "description": f"A focused study lobby for improving {topic}.",
                "match_reason": f"Recommended because your latest quiz showed difficulty in {topic}."
            })

    if not recommended_groups:
        recommended_groups.append({
            "group_id": 999,
            "group_name": "General Revision Squad",
            "focus_topic": "General Revision",
            "members_count": 3,
            "level": "Mixed",
            "description": "A general revision group for continued learning.",
            "match_reason": "Recommended because no major weak topic was detected."
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

def generate_learning_content_from_pdf_file(pdf_path, difficulty="Medium", quiz_type="MCQ Arena", question_count="5"):
    uploaded_file = None

    try:
        uploaded_file = client.files.upload(file=pdf_path)

        prompt = f"""
You are LevelUp AI.

Read the uploaded PDF and generate learning content from it.

Return ONLY valid JSON. No markdown. No explanation outside JSON.

JSON format:
{{
  "subject": "Detected subject name",
  "topics": ["topic 1", "topic 2", "topic 3"],
  "summary": "Short student-friendly summary",
  "quiz": [
    {{
      "id": 1,
      "question": "Question text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": "Correct option exactly as written",
      "topic": "Topic name",
      "difficulty": "{difficulty}"
    }}
  ],
  "flashcards": [
    {{
      "front": "Question side",
      "back": "Answer side",
      "topic": "Topic name"
    }}
  ]
}}

Rules:
- Generate exactly {question_count} quiz questions.
- Difficulty level: {difficulty}
- Quiz mode: {quiz_type}
- If quiz mode is True / False Match, use options ["True", "False"] only.
- If quiz mode is MCQ Arena, use exactly 4 options.
- Generate exactly 5 flashcards.
- Keep language simple.
- The answer must exactly match one option.
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded_file, prompt]
        )

        ai_text = response.text.strip()
        ai_text = ai_text.replace("```json", "").replace("```", "").strip()

        return json.loads(ai_text)

    finally:
        if uploaded_file is not None:
            try:
                client.files.delete(name=uploaded_file.name)
                print("Uploaded Gemini file deleted.")
            except Exception as delete_error:
                print("Could not delete uploaded Gemini file:", delete_error)

def get_safe_fallback_content(difficulty="Medium", quiz_type="MCQ Arena", question_count="5", reason="AI generation was unavailable."):
    fallback_quiz = [
        {
            "id": 1,
            "question": "What should a student do first after reading study material?",
            "options": [
                "Test understanding using active recall",
                "Ignore difficult topics",
                "Only change the file name",
                "Skip revision completely"
            ],
            "answer": "Test understanding using active recall",
            "topic": "Active Recall",
            "difficulty": difficulty
        },
        {
            "id": 2,
            "question": "Why are flashcards useful for revision?",
            "options": [
                "They support quick repeated practice",
                "They replace all learning",
                "They only store images",
                "They remove the need for quizzes"
            ],
            "answer": "They support quick repeated practice",
            "topic": "Flashcards",
            "difficulty": difficulty
        },
        {
            "id": 3,
            "question": "What does weak-topic analysis help identify?",
            "options": [
                "Concepts that need more practice",
                "The website background color",
                "The user's password",
                "Only the uploaded file name"
            ],
            "answer": "Concepts that need more practice",
            "topic": "Weak Topic Analysis",
            "difficulty": difficulty
        },
        {
            "id": 4,
            "question": "What is the benefit of XP in a learning platform?",
            "options": [
                "It rewards progress and keeps learners motivated",
                "It deletes wrong answers",
                "It disables revision",
                "It hides quiz results"
            ],
            "answer": "It rewards progress and keeps learners motivated",
            "topic": "Gamification",
            "difficulty": difficulty
        },
        {
            "id": 5,
            "question": "Why are study lobbies recommended?",
            "options": [
                "To help learners revise weak topics with peers",
                "To remove flashcards",
                "To stop quiz generation",
                "To skip learning analytics"
            ],
            "answer": "To help learners revise weak topics with peers",
            "topic": "Study Lobbies",
            "difficulty": difficulty
        }
    ]

    if question_count.isdigit():
        fallback_quiz = fallback_quiz[:int(question_count)]

    return {
        "subject": "Uploaded Study Material",
        "topics": [
            "Active Recall",
            "Flashcards",
            "Weak Topic Analysis",
            "Gamification",
            "Study Lobbies"
        ],
        "summary": f"{reason} LevelUp generated a safe revision session so the quiz, flashcards, dashboard, analytics, and study lobby flow can continue.",
        "quiz": fallback_quiz,
        "flashcards": [
            {
                "front": "What is active recall?",
                "back": "Active recall is a study method where learners test themselves by retrieving information from memory.",
                "topic": "Active Recall"
            },
            {
                "front": "Why are flashcards useful?",
                "back": "Flashcards help learners revise key ideas quickly through repeated practice.",
                "topic": "Flashcards"
            },
            {
                "front": "What is weak-topic analysis?",
                "back": "Weak-topic analysis identifies concepts where the learner made mistakes and needs more practice.",
                "topic": "Weak Topic Analysis"
            },
            {
                "front": "What does XP represent?",
                "back": "XP represents learning progress and rewards the student for completing activities.",
                "topic": "Gamification"
            },
            {
                "front": "What are study lobbies?",
                "back": "Study lobbies are peer learning spaces recommended based on weak topics or revision needs.",
                "topic": "Study Lobbies"
            }
        ],
        "extracted_text": reason,
        "config": {
            "difficulty": difficulty,
            "quiz_type": quiz_type,
            "question_count": question_count
        }
    }

@app.route("/api/process-file", methods=["POST"])
def process_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Get frontend configuration values
    difficulty = request.form.get("difficulty", "Medium")
    quiz_type = request.form.get("quiz_type", "MCQ Arena")
    question_count = request.form.get("question_count", "5")

    filename = secure_filename(uploaded_file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    uploaded_file.save(file_path)

    extracted_text = ""
    if filename.lower().endswith(".pdf"):
        try:
            response = generate_learning_content_from_pdf_file(
                file_path,
                difficulty=difficulty,
                quiz_type=quiz_type,
                question_count=question_count
            )

            response["extracted_text"] = "PDF processed directly using Gemini Files API."
            response["config"] = {
                "difficulty": difficulty,
                "quiz_type": quiz_type,
                "question_count": question_count
            }

            return jsonify(response)

        except Exception as pdf_gemini_error:
            print("Gemini PDF Files API failed:", pdf_gemini_error)
            print("Returning safe fallback content because Gemini PDF processing failed.")

            return jsonify(get_safe_fallback_content(
                difficulty=difficulty,
                quiz_type=quiz_type,
                question_count=question_count,
                reason="PDF uploaded successfully, but Gemini PDF processing was unavailable."
            ))

    # OCR extraction
    try:
        if ocr_engine:
            extracted_text = ocr_engine.extract_content(file_path)
        else:
            extracted_text = ""
    except Exception as ocr_error:
        print("OCR extraction error:", ocr_error)
        extracted_text = ""

    # Fallback text if OCR fails
    if not extracted_text or extracted_text.startswith("Error") or extracted_text.startswith("Extraction Error"):
        extracted_text = """
        Photosynthesis is the process by which green plants make food using sunlight,
        carbon dioxide and water. Chlorophyll captures sunlight for photosynthesis.
        Respiration releases energy from glucose. Genetics is the study of heredity
        and DNA.
        """

    # Gemini generation
    try:
        response = generate_learning_content_with_gemini(
            extracted_text,
            difficulty=difficulty,
            quiz_type=quiz_type,
            question_count=question_count
        )

        response["extracted_text"] = extracted_text[:1000]
        response["config"] = {
            "difficulty": difficulty,
            "quiz_type": quiz_type,
            "question_count": question_count
        }

        return jsonify(response)

    except Exception as gemini_error:
        print("Gemini error after OCR:", gemini_error)

        return jsonify(get_safe_fallback_content(
            difficulty=difficulty,
            quiz_type=quiz_type,
            question_count=question_count,
            reason="File was processed, but Gemini quiz generation was unavailable."
        ))
@app.route("/api/doubt", methods=["POST"])
def solve_doubt():
    try:
        data = request.get_json()

        question = data.get("question", "").strip()
        context = data.get("context", "").strip()

        if not question:
            return jsonify({"error": "No question provided"}), 400

        prompt = f"""
You are LevelUp Core Agent, an AI study assistant.

Answer the student's doubt clearly and simply.

Use the uploaded notes context if relevant.
If the context is not enough, give a helpful general explanation.

Keep the answer student-friendly.

Uploaded notes context:
{context[:4000]}

Student doubt:
{question}
"""

        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )

            answer = response.text.strip()

            return jsonify({
                "answer": answer,
                "source": "Gemini AI"
            })

        except Exception as gemini_error:
            print("Gemini doubt solver failed:", gemini_error)

            fallback_answer = generate_local_doubt_fallback(question, context)

            return jsonify({
                "answer": fallback_answer,
                "source": "Local fallback"
            })

    except Exception as e:
        print("Doubt solver route error:", e)
        return jsonify({
            "answer": "I could not process this doubt right now. Try asking a shorter question or generate notes again from the Quiz Generator.",
            "source": "Error fallback"
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)