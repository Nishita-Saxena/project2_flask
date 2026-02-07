from flask import Flask, render_template, request, redirect, url_for, session
from google import genai
import json

app = Flask(__name__)
app.secret_key = "hackathon-secret"

client = genai.Client(api_key="AIzaSyB-OnMeN6E1vvrGj60M6sUPdIm0ciUK-PY")

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

When interview ends, return JSON scorecard with:
clarity, technical_accuracy, completeness, confidence,
strengths, improvements, feedback.
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

Generate next question.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text.strip()


# -------- SCORECARD GENERATION ----------
def evaluate_answers():
    role = session["role"]
    qa_text = "\n".join(
        [f"Q:{a['question']}\nA:{a['answer']}" for a in session["answers"]]
    )

    prompt = f"""
{SYSTEM_PROMPT}

ROLE: {role}

INTERVIEW TRANSCRIPT:
{qa_text}

Interview finished. Generate scorecard JSON.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    try:
        return json.loads(response.text)
    except:
        return {"feedback": response.text}


# ---------------- INTERVIEW ----------------
@app.route("/interview", methods=["GET", "POST"])
def interview():
    if request.method == "POST":
        answer = request.form.get("answer")

        session["answers"].append({
            "question": session["questions"][session["q_index"]],
            "answer": answer
        })

        session["q_index"] += 1

        if session["q_index"] >= 5:
            return redirect(url_for("scorecard"))

    if len(session["questions"]) <= session["q_index"]:
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

