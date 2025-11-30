import pickle
import streamlit as st
import pandas as pd
import requests
import os
import time
TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"


# Function to download files from Dropbox
def download_file_from_dropbox(url, destination):
    if not os.path.exists(destination):
        with st.spinner(f"Downloading required file: {destination}..."):
            try:

                for attempt in range(3):
                    response = requests.get(url, stream=True)
                    if response.status_code == 200:
                        break
                    time.sleep(2 ** attempt)
                response.raise_for_status()
                with open(destination, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            except requests.exceptions.RequestException as e:
                st.error(f"Error downloading {destination}: {e}")
                st.stop()
            except NameError:

                st.error("Error setting up download. Check dependencies.")
                st.stop()


SIMILARITY_URL = "https://www.dropbox.com/scl/fi/e270q7z0hlvev130e81b0/similarity.pkl?rlkey=gbaa2jzmlpimgj3rcb2c14dfc&st=w2e6wsiu&dl=1"
MOVIE_LIST_URL = "https://www.dropbox.com/scl/fi/bvst4jb32ki33xvdu0il6/movie_list.pkl?rlkey=j278g6cnds56nrs0ul0o4d1ct&st=tcgcfmas&dl=1"

# Ensure downloads run only once
if 'data_loaded' not in st.session_state:
    download_file_from_dropbox(SIMILARITY_URL, "similarity.pkl")
    download_file_from_dropbox(MOVIE_LIST_URL, "movie_list.pkl")
    st.session_state['data_loaded'] = True

# --- 2. LOAD DATA
try:
    movies_dict = pickle.load(open("movie_list.pkl", "rb"))
    movies = pd.DataFrame(movies_dict)
    similarity = pickle.load(open("similarity.pkl", "rb"))
except FileNotFoundError:
    st.error("Data files could not be loaded. Please check the Dropbox links.")
    st.stop()
except Exception as e:
    st.error(f"An unexpected error occurred loading data: {e}")
    st.stop()

# --- 3. APP UI AND LOGIC  ---

st.set_page_config(page_title="NextFlick", layout="wide")


netflix_theme_css = """
<style>

@import url('https://fonts.googleapis.com/css2?family=Helvetica+Neue:wght@400;700&display=swap');

/* Main app container */
[data-testid="stAppViewContainer"] {
    background-color: #141414; 
    font-family: 'Helvetica Neue', sans-serif;
}
/* Main Streamlit Title (hidden, replaced by custom header) */
h1 {
    display: none; 
}

/* Custom Header H1 */
.custom-header h1 {
    color: #E50914; 
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 0;
    font-size: 2rem;
    display: block; /* Make sure custom H1 is visible */
}

/* Custom Headline for "Discover Your Next Obsession" */
.custom-headline {
    color: #FFFFFF;
    font-size: 2.5rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
}
.custom-subtitle {
    color: #9ca3af;
    font-size: 1.125rem;
    margin-bottom: 2rem;
}

/* Sub-header styling (e.g., "Because you watched...") */
h3 {
    color: #FFFFFF;
    font-weight: 700;
}

/* Button Styling */
.stButton>button {
    background-color: #E50914;
    color: #FFFFFF;
    border: none;
    border-radius: 5px;
    font-weight: bold;
    padding: 10px 24px;
    transition: all 0.2s;
}
.stButton>button:hover {
    background-color: #F40612; 
    transform: scale(1.02);
}

/* Image and Hover Effects */
.stImage img {
    border-radius: 8px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.stImage img:hover {
    transform: scale(1.05); 
    box-shadow: 0 0 25px rgba(229, 9, 20, 0.7); 
}

/* Custom Query Card Styling (Mimics the border/background) */
.query-card-container {
    background-color: #1a1a1a;
    border: 4px solid #8B0000; /* Darker red border */
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 2rem;
}

/* Keyword Pill Styling */
.keyword-pill {
    background-color: #333;
    color: #ccc;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
    margin: 4px 4px 4px 0;
    display: inline-block;
}
/* Style for Similarity Score */
.similarity-score {
    color: #4ade80; /* Green color for positive score */
    font-weight: bold;
    margin-left: 8px;
    font-size: 1.1em;
}
</style>
"""
st.markdown(netflix_theme_css, unsafe_allow_html=True)




def render_header_navigation():

    st.markdown("""
        <div class="custom-header" style="
            background-color: #1a1a1a; 
            border-bottom: 2px solid #333; 
            padding: 1.5rem 0;
            margin: -24px -24px 20px -24px;
            width: calc(100% + 48px);
            display: flex;
            justify-content: space-between;
            align-items: center;
        ">
            <div style="padding-left: 24px;">
                <h1>NEXTFLICK</h1>
            </div>
            <!-- Removed: Navigation links -->
        </div>
    """, unsafe_allow_html=True)

    # Headline and Subtitle
    st.markdown('<div class="custom-headline">Discover Your Next Obsession</div>', unsafe_allow_html=True)



render_header_navigation()


@st.cache_data
def fetch_hollywood_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
        response = requests.get(url)
        data = response.json()
        poster_path = data.get('poster_path')
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500/{poster_path}"
    except:
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


    movies_list_with_scores = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:6]

    recommended_movies_data = []
    for i in movies_list_with_scores:
        movie_row = movies.iloc[i[0]]
        score = i[1]

        if language.lower() != 'all' and movie_row.get('origin', '').lower() != language.lower():
            continue

        recommended_movies_data.append({
            'row': movie_row,
            'score': score
        })

    return recommended_movies_data


def display_movie_details(movie_data):

    movie_row = movie_data['row']
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


def render_query_movie_card(movie_row):
    title = movie_row.get('title', 'N/A')
    origin = movie_row.get('origin', 'N/A')
    overview_data = movie_row.get('overview')
    overview_text = ' '.join(overview_data) if isinstance(overview_data, list) else "No description available."
    director = ", ".join([name.title() for name in movie_row.get('crew', [])]) if movie_row.get('crew') else 'N/A'
    cast = ", ".join([name.title() for name in movie_row.get('cast', [])]) if movie_row.get('cast') else 'N/A'

    genres_from_row = getattr(movie_row, 'genres', [])
    genres = [g.title() for g in genres_from_row if isinstance(g, str)]

    keywords = [kw.replace(" ", "").title() for kw in movie_row.get('tags', '').split() if
                kw not in ['a', 'the', 'is', 'of']][:6]

    st.markdown('<div class="query-card-container">', unsafe_allow_html=True)

    col_poster, col_details = st.columns([1, 2.5])

    with col_poster:
        st.image(get_poster_url(movie_row), use_container_width=True)

    with col_details:
        st.markdown(
            f'<h3 style="font-size: 2rem; color: #FFFFFF; font-weight: 700; margin-bottom: 0.5rem;">{title}</h3>',
            unsafe_allow_html=True)
        st.markdown(f'<p style="color: #9ca3af; margin-bottom: 1rem;">{origin} | {", ".join(genres)}</p>',
                    unsafe_allow_html=True)

        st.markdown(f"**Overview:** {overview_text}")
        st.markdown(f"**Director:** {director}")
        st.markdown(f"**Cast:** {cast}")



    st.markdown('</div>', unsafe_allow_html=True)

# --- TABS ---
tab1, tab2 = st.tabs(["Recommend by Movie", " Browse by Genre"])

with tab1:


    col1, col2, col3 = st.columns([1.5, 3, 1])

    with col1:
        language_choice_rec = st.selectbox("Filter by Region:", ["All", "Hollywood", "Bollywood"], key="rec_lang")

    with col2:

        search_query = st.text_input("Search for a movie:", key="movie_search")

    with col3:

        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)  # Spacer for visual alignment
        if st.button("Recommend", use_container_width=True):
            st.session_state['run_recommendation'] = True
        else:
            st.session_state['run_recommendation'] = False

    # --- SEARCH/SELECTION LOGIC ---
    if language_choice_rec.lower() != 'all':
        filtered_movies = movies[movies['origin'].str.lower() == language_choice_rec.lower()]
    else:
        filtered_movies = movies

    selected_movie_name = None

    if search_query:
        matching_movies = filtered_movies[filtered_movies['title'].str.contains(search_query, case=False)][
            'title'].tolist()

        if not matching_movies:
            st.warning(f"No movies found with '{search_query}' in {language_choice_rec}.")
        else:
            # Present selection box if matches are found
            selected_movie_name = st.selectbox("Select movie from search results:", matching_movies,
                                               key="rec_movie_select")
    else:
        # Default selectbox if no search query
        selected_movie_name = st.selectbox("Or select from the entire list:", filtered_movies['title'].values,
                                           key="rec_movie_select_full")

    # --- RECOMMENDATION TRIGGER AND OUTPUT ---
    if st.session_state.get('run_recommendation', False):
        if selected_movie_name:
            with st.spinner(f'Finding similar movies for {selected_movie_name}...'):


                query_movie_row = movies[movies['title'] == selected_movie_name].iloc[0]
                render_query_movie_card(query_movie_row)


                recommendations_data = recommend(selected_movie_name, language=language_choice_rec)


                if recommendations_data:
                    st.markdown(f"### Because you watched **{selected_movie_name}**")
                    cols = st.columns(5)

                    for i, rec_data in enumerate(recommendations_data):
                        movie_row = rec_data['row']
                        similarity_score = rec_data['score']
                        # Convert score to percentage and format to 1 decimal place
                        score_percent = f"{similarity_score * 100:.1f}%"

                        with cols[i]:
                            st.image(get_poster_url(movie_row), use_container_width=True)


                            st.caption(
                                f"**{movie_row.get('title', '')}** ({movie_row.get('origin', '')})"
                                f"<span class='similarity-score'>{score_percent}</span>",
                                unsafe_allow_html=True
                            )
                            display_movie_details(rec_data)
                else:
                    st.info(f"Sorry, no {language_choice_rec} recommendations were found for '{selected_movie_name}'.")
        else:
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

                        display_movie_details({'row': movie_row})
        else:
            st.write(f"No {selected_genre} movies found.")
