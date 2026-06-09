from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import sqlite3
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. ĐỒNG BỘ ĐƯỜNG DẪN
DB_PATH = "movies.db"
FAISS_INDEX_PATH = "movies.index"
# Đảm bảo đường dẫn này trỏ đúng vào thư mục processed như trong ảnh Explorer của bạn
RAW_CSV_PATH = os.path.join("..", "data", "processed", "d1.csv")

print("🤖 Loading AI Semantic Model... Please wait...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

def build_big_data_index():
    """Hàm chạy 1 lần duy nhất để nạp file d1.csv 134k dòng vào SQLite và FAISS"""
    if not os.path.exists(RAW_CSV_PATH):
        print(f"❌ Không tìm thấy file dữ liệu lớn tại: {RAW_CSV_PATH}")
        return False
    
    print("⏳ Bước 1/3: Đang đọc file d1.csv khổng lồ...")
    df = pd.read_csv(RAW_CSV_PATH).fillna("")
    
    # Chuẩn hóa tên cột plot
    plot_col = 'Plot' if 'Plot' in df.columns else 'plot'
    
    print("📦 Bước 2/3: Đang lưu cấu trúc text vào Database SQLite để tìm kiếm từ khóa siêu tốc...")
    conn = sqlite3.connect(DB_PATH)
    df.to_sql("movies", conn, if_exists="replace", index=True, index_label="id")
    conn.close()
    
    print("🧠 Bước 3/3: AI đang dịch 134.164 cốt truyện thành ma trận Vector...")
    print("⚠️  CẢNH BÁO: Quá trình này rất nặng, mất khoảng 15-20 phút. Đừng tắt Terminal nhé!")
    
    plots = df[plot_col].tolist()
    embeddings = model.encode(plots, show_progress_bar=True, batch_size=64)
    
    print("⚡ Đang tối ưu cấu trúc lưu trữ bằng FAISS...")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    
    faiss.normalize_L2(embeddings)
    index.add(np.array(embeddings).astype('float32'))
    
    faiss.write_index(index, FAISS_INDEX_PATH)
    print("✅ ĐÃ ĐÓNG GÓI TOÀN BỘ DỮ LIỆU LỚN THÀNH CÔNG!")
    return True

# TỰ ĐỘNG KHỞI TẠO FILE NẾU CHƯA CÓ DỮ LIỆU ĐÓNG GÓI
if not os.path.exists(DB_PATH) or not os.path.exists(FAISS_INDEX_PATH):
    print("✨ Phát hiện chạy dữ liệu d1.csv lần đầu tiên. Tiến hành tiền xử lý...")
    build_big_data_index()

# Nạp file Index FAISS lên RAM
if os.path.exists(FAISS_INDEX_PATH):
    print("⚡ FAISS Index and SQLite Database for Big Data are online!")
    faiss_index = faiss.read_index(FAISS_INDEX_PATH)
else:
    faiss_index = None

@app.get("/api/search")
def search_movies(keyword: str = Query(default="")):
    if faiss_index is None or not os.path.exists(DB_PATH):
        return {"error": "Cơ sở dữ liệu lớn chưa được khởi tạo thành công!"}
    
    keyword_clean = keyword.strip()
    
    # Nếu trống, trả về 10 phim làm mẫu
    if not keyword_clean:
        conn = sqlite3.connect(DB_PATH)
        df_res = pd.read_sql_query("SELECT * FROM movies LIMIT 10", conn)
        conn.close()
        return df_res.to_dict(orient="records")
    
    # Kết nối vào Database SQLite
    conn = sqlite3.connect(DB_PATH)
    
    # Đọc trước các tên cột thực tế để tránh lỗi chữ hoa/thường
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movies LIMIT 1")
    col_names = [description[0] for description in cursor.description]
    
    title_col = 'Title' if 'Title' in col_names else 'title'
    genre_col = 'Genre' if 'Genre' in col_names else 'genre'
    plot_col = 'Plot' if 'Plot' in col_names else 'plot'
    origin_col = 'Origin' if 'Origin' in col_names else 'origin'
    cast_col = 'Cast' if 'Cast' in col_names else 'cast'
    
    # =========================================================================
    # TRƯỜNG HỢP 1: Nhập đoạn văn dài (Từ 5 từ trở lên) -> KÍCH HOẠT VŨ TRỤ AI FAISS
    # =========================================================================
    if len(keyword_clean.split()) >= 5:
        # Biến câu tìm kiếm thành Vector và chuẩn hóa
        query_vector = model.encode([keyword_clean])
        faiss.normalize_L2(query_vector)
        
        # Quét tìm top 10 ID phim khớp nhất trong file index
        scores, indices = faiss_index.search(np.array(query_vector).astype('float32'), 10)
        matched_ids = [int(idx) for idx in indices[0].tolist() if idx != -1]
        
        if matched_ids:
            placeholders = ",".join(str(idx) for idx in matched_ids)
            df_res = pd.read_sql_query(f"SELECT * FROM movies WHERE id IN ({placeholders})", conn)
            
            # Đồng bộ kiểu dữ liệu để sort chính xác theo điểm số từ cao xuống thấp của AI
            df_res['id'] = df_res['id'].astype(int)
            df_res = df_res.set_index('id').reindex(matched_ids).dropna(how='all').reset_index()
        else:
            df_res = pd.DataFrame()
            
    # =========================================================================
    # TRƯỜNG HỢP 2: Nhập ngắn (Dưới 5 từ) -> TRA CỨU TỪ KHÓA SIÊU TỐC BẰNG SQLITE
    # =========================================================================
    else:
        keyword_like = f"%{keyword_clean}%"
        
        # Tạo chuỗi truy vấn chuẩn xác, không xuống dòng lỗi cú pháp
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
            params=(keyword_like, keyword_like, keyword_like, keyword_like, keyword_like)
        ).head(50)
        
    conn.close()
    return df_res.to_dict(orient="records")