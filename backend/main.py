from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. ĐỒNG BỘ ĐƯỜNG DẪN MỚI: Đi lùi ra ngoài 1 cấp (..) để từ backend truy cập vào thư mục data
if os.path.exists(os.path.join("..", "data", "processed", "t1.csv")):
    CSV_PATH = os.path.join("..", "data", "processed", "t1.csv")
elif os.path.exists(os.path.join("..", "t1.csv")):
    CSV_PATH = os.path.join("..", "t1.csv")
else:
    CSV_PATH = os.path.join("..", "data", "raw", "t1_raw.csv") if os.path.exists(os.path.join("..", "data", "raw", "t1_raw.csv")) else ""

# 2. KHỞI TẠO MÔ HÌNH AI: Tự động tải mô hình đa ngôn ngữ về máy ở lần chạy đầu tiên
print("🤖 Loading AI Semantic Model... Please wait...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# Đọc dữ liệu và tính toán sẵn ma trận tọa độ (Vector Embeddings) cho phim
if CSV_PATH and os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH)
    df = df.fillna("") # Khử các ô rỗng tránh lỗi ép kiểu
    
    # Đồng bộ tên cột Plot (viết hoa/viết thường)
    plot_col = 'Plot' if 'Plot' in df.columns else 'plot'
    
    print("🧠 AI is analyzing movie plots into vectors...")
    plot_embeddings = model.encode(df[plot_col].tolist(), show_progress_bar=False)
    print("✅ AI Database is ready!")
else:
    df = None
    plot_embeddings = None

@app.get("/api/search")
def search_movies(keyword: str = Query(default="")):
    global df, plot_embeddings
    
    if df is None or plot_embeddings is None:
        return {"error": f"Không tìm thấy file dữ liệu tại đường dẫn: {CSV_PATH}"}
    
    # Nếu ô tìm kiếm trống, trả về toàn bộ phim
    if not keyword.strip():
        return df.to_dict(orient="records")
    
    keyword_clean = keyword.strip()
    
    # TRƯỜNG HỢP 1: Nhập đoạn văn dài (Từ 5 từ trở lên) -> KÍCH HOẠT TÌM KIẾM NGỮ NGHĨA AI
    if len(keyword_clean.split()) >= 5:
        # Biến câu văn của người dùng thành tọa độ vector
        query_embedding = model.encode([keyword_clean])
        
        # Tính độ tương đồng toán học giữa câu nhập và toàn bộ cốt truyện phim
        similarities = cosine_similarity(query_embedding, plot_embeddings)[0]
        
        df_copy = df.copy()
        df_copy['similarity_score'] = similarities
        
        # Chỉ lấy những phim có độ trùng khớp hợp lý (>= 0.2) và lấy tối đa 10 phim tốt nhất
        results = df_copy[df_copy['similarity_score'] >= 0.2]
        results = results.sort_values(by='similarity_score', ascending=False).head(10)
        
    # TRƯỜNG HỢP 2: Nhập ngắn (Dưới 5 từ) -> GIỮ NGUYÊN BỘ LỌC TỪ KHÓA CHUẨN XÁC TOÀN DIỆN
    else:
        keyword_lower = keyword_clean.lower()
        
        title_col = 'Title' if 'Title' in df.columns else 'title'
        genre_col = 'Genre' if 'Genre' in df.columns else 'genre'
        plot_col = 'Plot' if 'Plot' in df.columns else 'plot'
        origin_col = 'Origin' if 'Origin' in df.columns else 'origin'
        cast_col = 'Cast' if 'Cast' in df.columns else 'cast'
        
        mask = (
            df[title_col].astype(str).str.lower().str.contains(keyword_lower, na=False) |
            df[genre_col].astype(str).str.lower().str.contains(keyword_lower, na=False) |
            df[plot_col].astype(str).str.lower().str.contains(keyword_lower, na=False) |
            df[origin_col].astype(str).str.lower().str.contains(keyword_lower, na=False) |
            df[cast_col].astype(str).str.lower().str.contains(keyword_lower, na=False)
        )
        results = df[mask]
        
    return results.to_dict(orient="records")