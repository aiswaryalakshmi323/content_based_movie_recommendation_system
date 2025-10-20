import pickle
import streamlit as st
import pandas as pd
import requests
import os

# --- 1. CONFIGURATION AND FILE DOWNLOADS ---

# Securely access the API key using st.secrets
# This line will read from your local .streamlit/secrets.toml file
TMDB_API_KEY = st.secrets.get("TMDB_API_KEY", "8265bd1679663a7ea12ac168da84d2e8")

# Function to download files from Dropbox
def download_file_from_dropbox(url, destination):
    if not os.path.exists(destination):
        with st.spinner(f"Downloading required file: {destination}..."):
            try:
                response = requests.get(url, stream=True)
                response.raise_for_status()
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except requests.exceptions.RequestException as e:
                st.error(f"Error downloading {destination}: {e}")
                st.stop()

# Your Dropbox URLs with dl=1
SIMILARITY_URL = "https://www.dropbox.com/scl/fi/e270q7z0hlvev130e81b0/similarity.pkl?rlkey=gbaa2jzmlpimgj3rcb2c14dfc&st=s05epaib&dl=1"
MOVIE_LIST_URL = "https://www.dropbox.com/scl/fi/bvst4jb32ki33xvdu0il6/movie_list.pkl?rlkey=j278g6cnds56nrs0ul0o4d1ct&st=ywz0kem2&dl=1"

# Trigger the downloads
download_file_from_dropbox(SIMILARITY_URL, "similarity.pkl")
download_file_from_dropbox(MOVIE_LIST_URL, "movie_list.pkl")


# --- 2. LOAD DATA (this part now works because files are downloaded) ---
try:
    movies_dict = pickle.load(open("movie_list.pkl", "rb"))
    movies = pd.DataFrame(movies_dict)
    similarity = pickle.load(open("similarity.pkl", "rb"))
except FileNotFoundError:
    st.error("Data files could not be loaded. Please check the Dropbox links.")
    st.stop()

# --- 3. APP UI AND LOGIC (Your original code from here) ---

st.set_page_config(page_title="MojFlix", layout="wide")

netflix_theme_css = """
<style>
/* Import a font similar to Netflix's font */
@import url('https://fonts.googleapis.com/css2?family=Helvetica+Neue:wght@400;700&display=swap');
/* Main background */
[data-testid="stAppViewContainer"] {
    background-color: #141414; /* Netflix's dark background color */
    font-family: 'Helvetica Neue', sans-serif;
}
/* Main title styling */
h1 {
    color: #E50914; /* Netflix Red */
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
}
/* Sub-header styling (e.g., "Because you watched...") */
h3 {
    color: #FFFFFF;
    font-weight: 700;
}
/* Button styling */
.stButton>button {
    background-color: #E50914; /* Netflix Red */
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    font-weight: bold;
    padding: 10px 24px;
    transition: all 0.2s;
}
.stButton>button:hover {
    background-color: #F40612; /* A brighter red on hover */
    transform: scale(1.05);
}
/* Movie Poster Image Styling */
.stImage img {
    border-radius: 8px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.stImage img:hover {
    transform: scale(1.05); /* Slightly enlarge poster on hover */
    box-shadow: 0 0 25px rgba(229, 9, 20, 0.7); /* Red glow effect */
}
/* Movie Caption Styling */
.st-emotion-cache-1l02z68 p {
    color: #FAFAFA;
    font-weight: bold;
    text-align: center;
}
</style>
"""
st.markdown(netflix_theme_css, unsafe_allow_html=True)
st.title("MojFlix")

# --- Helper Functions ---
@st.cache_data
def fetch_hollywood_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
        response = requests.get(url)
        data = response.json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500/{poster_path}"
    except :
        return None
    return None

def get_poster_url(row):
    url = None
    if row.get('origin') == 'Bollywood':
        url = row.get('poster_url')
    else:  # For Hollywood
        url = fetch_hollywood_poster(row.get('movie_id'))

    if not url or pd.isna(url):
        title = row.get('title', 'Movie')
        return f"https://via.placeholder.com/500x750.png?text={title.replace(' ', '+')}"
    return url

def recommend(movie_name, language="All"):
    try:
        movie_index = movies[movies['title'] == movie_name].index[0]
    except IndexError:
        return []

    distances = similarity[movie_index]
    movies_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movies_data = []
    for i in movies_list:
        row = movies.iloc[i[0]]
        if language.lower() != 'all' and row.get('origin', '').lower() != language.lower():
            continue
        recommended_movies_data.append(row)

    return recommended_movies_data

tab1, tab2 = st.tabs(["Recommend by Movie", " Browse by Genre"])

def display_movie_details(movie_row):
    with st.expander("More Info"):
        overview_data = movie_row.get('overview')
        overview_text = ' '.join(overview_data) if isinstance(overview_data, list) else "No description available."
        st.write(f"**Description:** {overview_text}")

        cast_list = movie_row.get('cast')
        if cast_list and isinstance(cast_list, list):
            cast_display = ", ".join([name.title() for name in cast_list])
            st.write(f"**Cast:** {cast_display}")

        crew_list = movie_row.get('crew')
        if crew_list and isinstance(crew_list, list):
            director_display = ", ".join([name.title() for name in crew_list])
            st.write(f"**Director:** {director_display}")

with tab1:
    language_choice_rec = st.selectbox("Filter by:", ["All", "Hollywood", "Bollywood"], key="rec_lang")

    # --- START: NEW SEARCH BOX LOGIC ---

    # 1. Create a text input box for the user to type in.
    search_query = st.text_input("Type a movie name to search:", key="movie_search")

    # 2. Filter the movies dataframe based on the language choice.
    if language_choice_rec.lower() != 'all':
        filtered_movies = movies[movies['origin'].str.lower() == language_choice_rec.lower()]
    else:
        filtered_movies = movies

    # 3. If the user has typed something, find matches.
    if search_query:
        # Find titles that contain the search query (case-insensitive)
        matching_movies = filtered_movies[filtered_movies['title'].str.contains(search_query, case=False)]['title'].tolist()

        # If no matches, show a warning. Otherwise, show the selectbox with only the matches.
        if not matching_movies:
            st.warning("No movies found with that name in the selected filter.")
            selected_movie_name = None
        else:
            selected_movie_name = st.selectbox("Select a movie from the results:", matching_movies, key="rec_movie")
    else:
        # If nothing is typed, show the selectbox with all filtered movies (optional, can be removed)
        selected_movie_name = st.selectbox("Or select a movie from the list:", filtered_movies['title'].values, key="rec_movie")

    # --- END: NEW SEARCH BOX LOGIC ---

    if st.button("Recommend"):
        # We need to check if a movie was actually selected
        if selected_movie_name:
            with st.spinner('Finding similar movies...'):
                # Pass the language choice directly to the recommend function (it's good practice)
                recommendations = recommend(selected_movie_name, language=language_choice_rec)

            if recommendations:
                st.markdown(f"### Because you watched **{selected_movie_name}**")
                cols = st.columns(5)
                for i, movie_row in enumerate(recommendations):
                    with cols[i]:
                        st.image(get_poster_url(movie_row), use_container_width=True)
                        st.caption(f"**{movie_row.get('title', '')}** ({movie_row.get('origin', '')})")
                        display_movie_details(movie_row)
            else:
                st.info(f"Sorry, no {language_choice_rec} recommendations were found for '{selected_movie_name}'.")
        else
            st.warning("Please select a movie first.")

with tab2:
    genre_list = ["Action", "Adventure", "Comedy", "Drama", "Romance", "Thriller", "Crime", "Family"]
    language_choice_genre = st.selectbox("Filter by:", ["All", "Hollywood", "Bollywood"], key="genre_lang")
    selected_genre = st.selectbox("Select a genre to browse:", genre_list, key="genre_select")

    if st.button("Show Movies"):
        with st.spinner(f'Finding {selected_genre} movies...'):
            genre_movies = movies[movies['tags'].str.contains(selected_genre.lower().replace(" ", ""), na=False)]
            if language_choice_genre.lower() != 'all':
                genre_movies = genre_movies[genre_movies['origin'].str.lower() == language_choice_genre.lower()]

        if not genre_movies.empty:
            st.markdown(f"### Top {selected_genre} Movies ({language_choice_genre})")
            num_movies = min(len(genre_movies), 10)
            cols_per_row = 5
            for i in range(0, num_movies, cols_per_row):
                cols = st.columns(cols_per_row)
                batch = genre_movies.iloc[i:i + cols_per_row]
                for j, (idx, movie_row) in enumerate(batch.iterrows()):
                    with cols[j]:
                        st.image(get_poster_url(movie_row), use_container_width=True)
                        st.caption(f"**{movie_row.get('title', '')}** ({movie_row.get('origin', '')})")
                        display_movie_details(movie_row)
        else:
            st.write(f"No {selected_genre} movies found.")