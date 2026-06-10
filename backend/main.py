from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
import os
import sqlite3
import numpy as np
import faiss

from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv
from openai import OpenAI

# ==================================================
# ENVIRONMENT
# ==================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# ==================================================
# FASTAPI
# ==================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================
# PATHS
# ==================================================

DB_PATH = "movies.db"
FAISS_INDEX_PATH = "movies.index"
RAW_CSV_PATH = os.path.join(
    "..",
    "data",
    "processed",
    "d1.csv"
)

# ==================================================
# LOAD EMBEDDING MODEL
# ==================================================

print("🤖 Loading Semantic Model...")

embedding_model = SentenceTransformer(
    "paraphrase-multilingual-MiniLM-L12-v2"
)

# ==================================================
# BUILD DATABASE + FAISS
# ==================================================

def build_big_data_index():

    if not os.path.exists(RAW_CSV_PATH):
        print(f"❌ Cannot find {RAW_CSV_PATH}")
        return False

    print("📖 Reading CSV...")
    df = pd.read_csv(RAW_CSV_PATH).fillna("")

    plot_col = "Plot" if "Plot" in df.columns else "plot"

    print("💾 Saving SQLite Database...")

    conn = sqlite3.connect(DB_PATH)

    df.to_sql(
        "movies",
        conn,
        if_exists="replace",
        index=True,
        index_label="id"
    )

    conn.close()

    print("🧠 Creating embeddings...")

    plots = df[plot_col].tolist()

    embeddings = embedding_model.encode(
        plots,
        show_progress_bar=True,
        batch_size=64
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)

    faiss.normalize_L2(embeddings)

    index.add(
        np.array(embeddings).astype("float32")
    )

    faiss.write_index(
        index,
        FAISS_INDEX_PATH
    )

    print("✅ FAISS Index Created")

    return True


# ==================================================
# FIRST RUN
# ==================================================

if (
    not os.path.exists(DB_PATH)
    or
    not os.path.exists(FAISS_INDEX_PATH)
):
    print("✨ First startup detected")
    build_big_data_index()

# ==================================================
# LOAD FAISS
# ==================================================

if os.path.exists(FAISS_INDEX_PATH):

    faiss_index = faiss.read_index(
        FAISS_INDEX_PATH
    )

    print("⚡ FAISS Loaded")

else:

    faiss_index = None

# ==================================================
# SEARCH FUNCTION
# ==================================================

def search_movies_internal(keyword: str):

    if (
        faiss_index is None
        or
        not os.path.exists(DB_PATH)
    ):
        return []

    keyword_clean = keyword.strip()

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM movies LIMIT 1"
    )

    col_names = [
        desc[0]
        for desc in cursor.description
    ]

    title_col = "Title" if "Title" in col_names else "title"
    genre_col = "Genre" if "Genre" in col_names else "genre"
    plot_col = "Plot" if "Plot" in col_names else "plot"
    origin_col = "Origin" if "Origin" in col_names else "origin"
    cast_col = "Cast" if "Cast" in col_names else "cast"

    # ==========================================
    # SEMANTIC SEARCH
    # ==========================================

    if len(keyword_clean.split()) >= 5:

        query_vector = embedding_model.encode(
            [keyword_clean]
        )

        faiss.normalize_L2(query_vector)

        scores, indices = faiss_index.search(
            np.array(query_vector).astype(
                "float32"
            ),
            10
        )

        matched_ids = [
            int(idx)
            for idx in indices[0].tolist()
            if idx != -1
        ]

        if matched_ids:

            placeholders = ",".join(
                str(idx)
                for idx in matched_ids
            )

            df_res = pd.read_sql_query(
                f"""
                SELECT *
                FROM movies
                WHERE id IN ({placeholders})
                """,
                conn
            )

            df_res["id"] = (
                df_res["id"]
                .astype(int)
            )

            df_res = (
                df_res
                .set_index("id")
                .reindex(matched_ids)
                .dropna(how="all")
                .reset_index()
            )

        else:

            df_res = pd.DataFrame()

    # ==========================================
    # KEYWORD SEARCH
    # ==========================================

    else:

        keyword_like = f"%{keyword_clean}%"

        query_sql = (
            f"SELECT * FROM movies WHERE "
            f"{title_col} LIKE ? OR "
            f"{genre_col} LIKE ? OR "
            f"{plot_col} LIKE ? OR "
            f"{origin_col} LIKE ? OR "
            f"{cast_col} LIKE ?"
        )

        df_res = pd.read_sql_query(
            query_sql,
            conn,
            params=(
                keyword_like,
                keyword_like,
                keyword_like,
                keyword_like,
                keyword_like
            )
        ).head(50)

    conn.close()

    return df_res.to_dict(
        orient="records"
    )

# ==================================================
# GROQ GENERATION (RAG)
# ==================================================

def generate_movie_answer(user_query, movies):

    if not movies:
        return "I could not find any matching movie."

    context = ""

    for i, movie in enumerate(movies):

        title = (
            movie.get("Title")
            or movie.get("title")
            or "Unknown"
        )

        genre = (
            movie.get("Genre")
            or movie.get("genre")
            or ""
        )

        plot = (
            movie.get("Plot")
            or movie.get("plot")
            or ""
        )

        context += f"""
Movie {i+1}
Title: {title}
Genre: {genre}
Plot: {plot[:500]}
"""

    prompt = f"""
The user is trying to identify a movie.

User description:
{user_query}

Retrieved candidate movies:
{context}

Instructions:
- Choose the most likely movie.
- Explain why.
- Mention confidence level.
- Mention alternative matches.
- Use information only from the retrieved movies.
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a movie finder assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:

        print("Groq Error:", e)

        return f"Groq Error: {str(e)}"
# ==================================================
# API SEARCH
# ==================================================

@app.get("/api/search")
def search_movies(
    keyword: str = Query(default="")
):

    movies = search_movies_internal(
        keyword
    )

    return movies

# ==================================================
# API CHAT (RAG)
# ==================================================

@app.get("/api/chat")
def chat_movie(
    query: str
):

    movies = search_movies_internal(
        query
    )

    answer = generate_movie_answer(
        query,
        movies[:5]
    )

    return {
        "answer": answer,
        "movies": movies[:5]
    }