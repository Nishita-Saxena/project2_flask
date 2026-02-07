from flask import Flask, render_template, request, redirect, url_for, session
from google import genai
import json

app = Flask(__name__)
app.secret_key = "hackathon-secret"

# Gemini client
client = genai.Client(api_key="AIzaSyAhkAmAMv_Z-S8bLjM-PtEN4sXcYv6IbRY")


SYSTEM_PROMPT = """
You are an AI Interviewer and Interview Evaluator.

PHASE 1: Ask one role‑specific interview question at a time.
PHASE 2: Generate a structured scorecard after 5 questions.

Rules:
- Ask ONE question only.
- Total questions = 5.
- Do not repeat questions.
- Increase difficulty gradually.
- Use previous answers for context.
- Do not evaluate during interview.
"""

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")


# ---------------- SETUP ----------------
@app.route("/setup", methods=["GET", "POST"])
def setup():
    if request.method == "POST":
        session["name"] = request.form["name"]
        session["role"] = request.form["role"]
        session["answers"] = []
        session["questions"] = []
        session["q_index"] = 0
        return redirect(url_for("interview"))

    return render_template("setup.html")


# -------- QUESTION GENERATION ----------
def generate_question():
    role = session["role"]

    history = "\n".join(
        [f"Q:{a['question']}\nA:{a['answer']}" for a in session["answers"]]
    )

    prompt = f"""
{SYSTEM_PROMPT}

ROLE: {role}
QUESTION NUMBER: {session['q_index'] + 1}

INTERVIEW HISTORY:
{history}

Generate the next interview question.
Output ONLY the question text.
Do not include labels like "Question 1".
Do not include commentary.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()

    # Clean formatting issues
    text = text.replace("**", "")

    if "Question" in text:
        text = text.split("Question")[-1]
        text = "Question " + text

    if ":" in text:
        text = text.split(":", 1)[1].strip()

    return text
# -------- SCORECARD GENERATION ----------
def evaluate_answers():
    role = session["role"]

    qa_text = "\n".join(
        [f"Q:{a['question']}\nA:{a['answer']}" for a in session["answers"]]
    )

    prompt = f"""
Return ONLY valid JSON.

Evaluate this interview for role: {role}

{qa_text}

JSON format:
{{
  "clarity": 1-10,
  "technical_accuracy": 1-10,
  "completeness": 1-10,
  "confidence": 1-10,
  "strengths": ["point", "point"],
  "improvements": ["point", "point"],
  "feedback": "short summary"
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    print(response.text)

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except Exception as e:
        print("JSON parse failed:", e)
        print("RAW:", text)
        return {
            "clarity": "",
            "technical_accuracy": "",
            "completeness": "",
            "confidence": "",
            "strengths": [],
            "improvements": [],
            "feedback": text
        }


# ---------------- INTERVIEW ----------------
@app.route("/interview", methods=["GET", "POST"])
def interview():

    # Ensure first question exists
    if len(session["questions"]) == 0:
        session["questions"].append(generate_question())

    if request.method == "POST":
        answer = request.form.get("answer")

        session["answers"].append({
            "question": session["questions"][session["q_index"]],
            "answer": answer
        })

        session["q_index"] += 1

        if session["q_index"] >= 5:
            return redirect(url_for("scorecard"))

        # Generate next question
        session["questions"].append(generate_question())

    return render_template(
        "interview.html",
        question=session["questions"][session["q_index"]],
        history=session["answers"]
    )


# ---------------- SCORECARD ----------------
@app.route("/scorecard")
def scorecard():
    scores = evaluate_answers()

    return render_template(
        "scorecard.html",
        name=session.get("name"),
        role=session.get("role"),
        scores=scores,
        answers=session.get("answers")
    )


if __name__ == "__main__":
    app.run(debug=True)