from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

questions = [
    {"question": "What decade?", "options": ["1990's", "2000's", "2010's", "2020's"], "answer": "2000's"},
    {"question": "What genre?", "options": ["Thriller", "Drama", "Soap"], "answer": "Soap"},
    {"question": "Which actor?", "options": ["Leo", "Tom", "John"], "answer": "Leo"},
]

@app.route("/")
def index():
    return redirect(url_for("quiz", qnum=0))  # Start quiz at question 0

@app.route("/quiz/<int:qnum>", methods=["GET", "POST"])
def quiz(qnum):
    if qnum >= len(questions):
        return "<h1>Quiz Finished!</h1>"

    question = questions[qnum]

    if request.method == "POST":
        selected = request.form.get("option")
        correct = question["answer"]

        # move to next question
        return redirect(url_for("quiz", qnum=qnum+1))

    return render_template("quiz.html", question=question, qnum=qnum)
    

if __name__ == "__main__":
    app.run(debug=True)