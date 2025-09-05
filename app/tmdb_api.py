import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('TMDB_API_KEY')
BASE_URL = "https://api.themoviedb.org/3"

def get_popular_movies():
    url = f"{BASE_URL}/movie/popular"
    params = {
        "api_key": API_KEY,
        "language": "en-US",
        "page": 1
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()["results"][:10]
    return []

def get_movies_by_genre(genre_id):
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": API_KEY,
        "language": "en-US",
        "with_genres": genre_id,
        "sort_by": "popularity.desc",
        "page": 1
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()["results"][:8]
    return []

def get_movies_with_filters(genres=None, min_year=None, max_year=None, 
                           min_runtime=None, max_runtime=None, 
                           min_rating=None, sort_by="popularity.desc", page=1):
    url = f"{BASE_URL}/discover/movie"
    params = {
        "api_key": API_KEY,
        "language": "en-US",
        "page": page,
        "sort_by": sort_by
    }
    
    if genres:
        params["with_genres"] = ",".join(map(str, genres))
    if min_year:
        params["primary_release_date.gte"] = f"{min_year}-01-01"
    if max_year:
        params["primary_release_date.lte"] = f"{max_year}-12-31"
    if min_runtime:
        params["with_runtime.gte"] = min_runtime
    if max_runtime:
        params["with_runtime.lte"] = max_runtime
    if min_rating:
        params["vote_average.gte"] = min_rating
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()["results"][:8]
    return []
