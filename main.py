import os
from flask import Flask, render_template, request, session, redirect
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Watchlist, Watched
from app.tmdb_api import get_popular_movies, get_movies_by_genre, get_movies_with_filters, get_movie_details, search_movies
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Create Flask app
app = Flask(__name__, template_folder='app/templates', static_folder='app/static')

# Set secret key for sessions
app.secret_key = os.getenv('SECRET_KEY')

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'isolation_level': 'READ_COMMITTED'
}

# Initialize database and login manager
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (ValueError, TypeError):
        return None

# Quiz questions - each has genres and weights
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

# Home page - shows quiz start
@app.route("/")
def index():
    return render_template("quiz_start.html")

# Handle quiz questions and store answers in session
@app.route("/quiz/<int:question_num>", methods=["GET", "POST"])
@login_required
def quiz(question_num=0):
    session.permanent = True
    
    if request.method == "POST":
        # Store user's answer
        if 'answers' not in session:
            session['answers'] = []
        
        selected = int(request.form.get("option"))
        session['answers'].append(selected)
        session.modified = True
        
        # Go to next question or results
        next_question = question_num + 1
        if next_question < len(QUIZ_QUESTIONS):
            return redirect(f"/quiz/{next_question}")
        else:
            return redirect("/results")
    
    # Reset answers if starting over
    if question_num == 0 and request.method == "GET":
        session['answers'] = []
        session.modified = True
    
    # Redirect if question number is invalid
    if question_num >= len(QUIZ_QUESTIONS):
        return redirect("/results")
    
    question_data = QUIZ_QUESTIONS[question_num]
    return render_template("quiz_question.html", 
                         question=question_data,
                         question_num=question_num,
                         total_questions=len(QUIZ_QUESTIONS))

# Show popular movies - excludes ones user has already watched
@app.route("/movies")
@login_required
def movies():
    watched_movie_ids = [w.movie_id for w in Watched.query.filter_by(user_id=current_user.id).all()]
    
    # Get enough movies to ensure 20 after filtering
    all_movies = []
    page = 1
    while len(all_movies) < 20 and page <= 5:
        movies_data = get_popular_movies(page)
        if not movies_data:
            break
        
        for movie in movies_data:
            if movie['id'] not in watched_movie_ids:
                all_movies.append(movie)
                if len(all_movies) >= 20:
                    break
        page += 1
    
    return render_template("movies.html", movies=all_movies[:20], watched_movie_ids=watched_movie_ids)

# Process quiz answers and show recommended movies
@app.route("/results")
def results():
    if 'answers' not in session or len(session['answers']) == 0:
        return redirect("/")
    
    # Setup preferences object
    preferences = {
        'genres': [],
        'min_year': None,
        'max_year': None,
        'min_runtime': None,
        'max_runtime': None,
        'min_rating': None,
        'sort_by': 'popularity.desc'
    }
    
    # Calculate genre scores based on quiz answers 
    genre_scores = {}
    
    for i, answer in enumerate(session['answers']):
        if i < len(QUIZ_QUESTIONS):
            question = QUIZ_QUESTIONS[i]
            selected_option = question['options'][answer]
            
            # Add genre scores with weights
            if 'genres' in selected_option:
                for genre_id in selected_option['genres']:
                    weight = selected_option.get('weight', 1)
                    genre_scores[genre_id] = genre_scores.get(genre_id, 0) + weight
            
            # Set other preferences from quiz answers
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
    
    # Get top 3 genres based on scores
    if genre_scores:
        top_genres = sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        preferences['genres'] = [genre_id for genre_id, score in top_genres]
    
    # Save preferences for refreshing
    session['preferences'] = preferences
    
    # Filter out movies already watched
    if current_user.is_authenticated:
        watched_movie_ids = [w.movie_id for w in Watched.query.filter_by(user_id=current_user.id).all()]
    else:
        watched_movie_ids = []

    
    movies_data = get_movies_with_filters(**preferences, page=1)
    movies_data = [movie for movie in movies_data if movie['id'] not in watched_movie_ids]
    
    session.modified = True
    
    return render_template("results.html", movies=movies_data)

# Get new movie recommendations without retaking quiz
@app.route("/refresh")
def refresh():
    if 'preferences' not in session:
        return redirect("/")
    
    preferences = session['preferences']
    shown_movies = session.get('shown_movies', [])
    current_page = session.get('current_page', 1)
    
    # Get watched movies for logged-in users
    if current_user.is_authenticated:
        watched_movie_ids = [w.movie_id for w in Watched.query.filter_by(user_id=current_user.id).all()]
    else:
        watched_movie_ids = []

    
    # Try to get new movies from different pages
    max_attempts = 10
    attempts = 0
    new_movies = []
    
    while len(new_movies) < 8 and attempts < max_attempts:
        attempts += 1
        current_page += 1
        
        movies_data = get_movies_with_filters(**preferences, page=current_page)
        
        if not movies_data:
            break
            
        for movie in movies_data:
            if movie['id'] not in shown_movies and movie['id'] not in watched_movie_ids and len(new_movies) < 8:
                new_movies.append(movie)
    
    # If no new movies found - reset and show original
    if not new_movies:
        session['shown_movies'] = []
        session['current_page'] = 1
        movies_data = get_movies_with_filters(**preferences, page=1)
        new_movies = [movie for movie in movies_data if movie['id'] not in watched_movie_ids][:8]
        session['shown_movies'] = [movie['id'] for movie in new_movies]
    else:
        session['shown_movies'].extend([movie['id'] for movie in new_movies])
        session['current_page'] = current_page
    
    session.modified = True
    return render_template("results.html", movies=new_movies)

# Show detailed info for a movie
@app.route("/movie/<int:movie_id>")
def movie_details(movie_id):
    movie_data = get_movie_details(movie_id)
    if not movie_data:
        return redirect("/")
    
    is_watched = False
    if current_user.is_authenticated:
        is_watched = Watched.query.filter_by(user_id=current_user.id, movie_id=movie_id).first() is not None
    
    return render_template("movie_details.html", movie=movie_data, is_watched=is_watched)

# Mark a movie as watched
@app.route("/mark_watched/<int:movie_id>", methods=["POST"])
@login_required
def mark_watched(movie_id):
    movie_title = request.form.get("movie_title", "Unknown Movie")
    movie_poster = request.form.get("movie_poster", "")
    
    # Only add if not already watched
    existing = Watched.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if not existing:
        watched_movie = Watched(user_id=current_user.id, movie_id=movie_id, movie_title=movie_title, movie_poster=movie_poster)
        db.session.add(watched_movie)
        db.session.commit()
    
    return redirect(request.referrer or "/")

# User registration
@app.route("/register", methods=["GET", "POST"])
def register():
    print(f"Register route called with method: {request.method}")
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        print(f"Attempting to register: {username}, {email}")

        # Check if all fields filled
        if not username or not email or not password:
            print("Missing fields")
            return render_template("register.html", error="All fields are required")
        
        # Check if username taken
        if User.query.filter_by(username=username).first():
            print("Username exists")
            return render_template("register.html", error="Username already exists")
        
        # Check if email taken
        if User.query.filter_by(email=email).first():
            print("Email exists")
            return render_template("register.html", error="Email already registered")
        
        # Create new user and log them in
        try:
            print("Creating user...")
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            print("About to commit...")
            db.session.commit()
            
            print(f"User created with ID: {user.id}")
            
            # Verify the user was actually saved
            saved_user = User.query.filter_by(username=username).first()
            if saved_user:
                print(f"Verification: User {saved_user.username} found in database")
            else:
                print("ERROR: User not found after commit!")

            login_user(user)
            return redirect("/")
        except Exception as e:
            print(f"Database error: {e}")
            db.session.rollback()
            return render_template("register.html", error="Registration failed")
    
    return render_template("register.html")


# User login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Check fields provided
        if not username or not password:
            return render_template("login.html", error="Username and password are required")

        # Find user and check password
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect("/")
        else:
            return render_template("login.html", error="Invalid username or password")
    
    return render_template("login.html")

# Log out user
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")
    
# Show user's watched movies
@app.route("/watched")
@login_required
def watched_list():
    watched_movies = Watched.query.filter_by(user_id=current_user.id).order_by(Watched.watched_at.desc()).all()
    return render_template("watched.html", watched_movies=watched_movies)

# Search for movies
@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            return redirect(f"/search?q={query}")
    
    query = request.args.get("q", "")
    movies_data = []
    
    if query:
        movies_data = search_movies(query)
        
        # Filter out watched movies for logged-in users
        if current_user.is_authenticated:
            watched_movie_ids = [w.movie_id for w in Watched.query.filter_by(user_id=current_user.id).all()]
            movies_data = [movie for movie in movies_data if movie['id'] not in watched_movie_ids]
    
    return render_template("search.html", movies=movies_data, query=query)

# Run the app
if __name__ == "__main__":
    app.run(debug=True)
