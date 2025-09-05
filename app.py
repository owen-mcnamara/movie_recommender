import random
from flask import Flask, render_template, request, session, redirect
from app.tmdb_api import get_popular_movies, get_movies_by_genre, get_movies_with_filters

app = Flask(__name__, 
            template_folder='app/templates',
            static_folder='app/static')

app.secret_key = 'movie-quiz-secret-key-2024'  # For flask sessions

# Quiz questions data
QUIZ_QUESTIONS = [
    {
        "question": "What's your ideal Friday night?",
        "options": [
            {"text": "Intense action and explosions", "genres": [28], "weight": 2},
            {"text": "Laughing with friends", "genres": [35], "weight": 2},
            {"text": "Deep emotional story", "genres": [18], "weight": 2},
            {"text": "Getting scared", "genres": [27], "weight": 2}
        ]
    },
    {
        "question": "How much time do you have?",
        "options": [
            {"text": "Quick watch (under 90 min)", "max_runtime": 90, "weight": 1},
            {"text": "Standard movie (90-120 min)", "min_runtime": 90, "max_runtime": 120, "weight": 1},
            {"text": "Epic experience (2+ hours)", "min_runtime": 120, "weight": 1},
            {"text": "I don't care about length", "weight": 0}
        ]
    },
    {
        "question": "What era appeals to you?",
        "options": [
            {"text": "Classic films (before 1980)", "max_year": 1979, "weight": 1},
            {"text": "80s & 90s nostalgia", "min_year": 1980, "max_year": 1999, "weight": 1},
            {"text": "Modern movies (2000s-2010s)", "min_year": 2000, "max_year": 2019, "weight": 1},
            {"text": "Latest releases (2020+)", "min_year": 2020, "weight": 1}
        ]
    },
    {
        "question": "What kind of quality are you looking for?",
        "options": [
            {"text": "Critically acclaimed (8+ rating)", "min_rating": 8.0, "sort": "vote_average.desc", "weight": 1},
            {"text": "Popular crowd-pleasers", "sort": "popularity.desc", "weight": 1},
            {"text": "Hidden gems (fewer votes)", "sort": "vote_count.asc", "weight": 1},
            {"text": "I'm not picky", "weight": 0}
        ]
    },
    {
        "question": "What setting excites you most?",
        "options": [
            {"text": "Space and future", "genres": [878], "weight": 1},
            {"text": "Fantasy worlds", "genres": [14], "weight": 1},
            {"text": "Real world drama", "genres": [18], "weight": 1},
            {"text": "Crime and mystery", "genres": [80, 9648], "weight": 1}
        ]
    },
    {
        "question": "How do you want to feel afterward?",
        "options": [
            {"text": "Pumped and energized", "genres": [28, 12], "weight": 2},
            {"text": "Happy and uplifted", "genres": [35, 10751], "weight": 2},
            {"text": "Thoughtful and moved", "genres": [18], "weight": 2},
            {"text": "Thrilled and tense", "genres": [53, 27], "weight": 2}
        ]
    }
]


@app.route("/")
def index():
    return render_template("quiz_start.html")

@app.route("/quiz", methods=["GET", "POST"])
@app.route("/quiz/<int:question_num>", methods=["GET", "POST"])
def quiz(question_num=0):
    session.permanent = True  # Add this line
    
    if request.method == "POST":
        # Store the answer
        if 'answers' not in session:
            session['answers'] = []
        
        selected = int(request.form.get("option"))
        session['answers'].append(selected)
        session.modified = True  # Force session save
        print(f"Added answer {selected}, total answers: {len(session['answers'])}")
        print(f"Session contents: {session['answers']}")
        
        # Move to next question or results
        next_question = question_num + 1
        if next_question < len(QUIZ_QUESTIONS):
            return redirect(f"/quiz/{next_question}")
        else:
            return redirect("/results")
    
    # Only reset answers on first question AND if it's a GET request (fresh start)
    if question_num == 0 and request.method == "GET":
        session['answers'] = []
        session.modified = True  # Force session save
        print("Reset answers for fresh start")
    
    if question_num >= len(QUIZ_QUESTIONS):
        return redirect("/results")
    
    print(f"Current session at question {question_num}: {session.get('answers', [])}")
    
    question_data = QUIZ_QUESTIONS[question_num]
    return render_template("quiz_question.html", 
                         question=question_data,
                         question_num=question_num,
                         total_questions=len(QUIZ_QUESTIONS))

@app.route("/movies")
def movies():
    movies_data = get_popular_movies()
    return render_template("movies.html", movies=movies_data)

@app.route("/results")
def results():
    if 'answers' not in session or len(session['answers']) == 0:
        return redirect("/")
    
    # Reset shown movies for fresh quiz results
    session['shown_movies'] = []
    session['current_page'] = 1
    
    # ... your existing preference logic ...
    preferences = {
        'genres': [],
        'min_year': None,
        'max_year': None,
        'min_runtime': None,
        'max_runtime': None,
        'min_rating': None,
        'sort_by': 'popularity.desc'
    }
    
    genre_scores = {}
    
    for i, answer in enumerate(session['answers']):
        if i < len(QUIZ_QUESTIONS):
            question = QUIZ_QUESTIONS[i]
            selected_option = question['options'][answer]
            
            if 'genres' in selected_option:
                for genre_id in selected_option['genres']:
                    weight = selected_option.get('weight', 1)
                    genre_scores[genre_id] = genre_scores.get(genre_id, 0) + weight
            
            if 'min_year' in selected_option:
                preferences['min_year'] = selected_option['min_year']
            if 'max_year' in selected_option:
                preferences['max_year'] = selected_option['max_year']
            if 'min_runtime' in selected_option:
                preferences['min_runtime'] = selected_option['min_runtime']
            if 'max_runtime' in selected_option:
                preferences['max_runtime'] = selected_option['max_runtime']
            if 'min_rating' in selected_option:
                preferences['min_rating'] = selected_option['min_rating']
            if 'sort' in selected_option:
                preferences['sort_by'] = selected_option['sort']
    
    if genre_scores:
        top_genres = sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        preferences['genres'] = [genre_id for genre_id, score in top_genres]
    
    # Store preferences for refresh
    session['preferences'] = preferences
    
    # Get first batch of movies
    movies_data = get_movies_with_filters(**preferences, page=1)
    
    # Track shown movies
    session['shown_movies'] = [movie['id'] for movie in movies_data]
    session.modified = True
    
    return render_template("results.html", movies=movies_data)


@app.route("/refresh")
def refresh():
    if 'preferences' not in session:
        return redirect("/")
    
    preferences = session['preferences']
    shown_movies = session.get('shown_movies', [])
    current_page = session.get('current_page', 1)
    
    # Try to find new movies
    max_attempts = 10
    attempts = 0
    new_movies = []
    
    while len(new_movies) < 8 and attempts < max_attempts:
        attempts += 1
        current_page += 1
        
        # Get movies from next page
        movies_data = get_movies_with_filters(**preferences, page=current_page)
        
        if not movies_data:  # No more movies available
            break
            
        # Filter out already shown movies
        for movie in movies_data:
            if movie['id'] not in shown_movies and len(new_movies) < 8:
                new_movies.append(movie)
    
    if not new_movies:
        # If no new movies found, reset and start over
        session['shown_movies'] = []
        session['current_page'] = 1
        new_movies = get_movies_with_filters(**preferences, page=1)[:8]
        session['shown_movies'] = [movie['id'] for movie in new_movies]
    else:
        # Add new movies to shown list
        session['shown_movies'].extend([movie['id'] for movie in new_movies])
        session['current_page'] = current_page
    
    session.modified = True
    
    return render_template("results.html", movies=new_movies)





if __name__ == "__main__":
    app.run(debug=True)

