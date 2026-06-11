CineGalaxy-AI-Search/
│
├── backend/
│   ├── main.py
│   ├── movies.db
│   ├── movies.index
│   ├── .env
│   ├── tests/
│   │   ├── test_gemini.py
│   │   ├── test_groq.py
│   │   └── test_models.py
│   
│
├── data/
│   ├── processed/
│   └── raw/
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── notebooks/
├── README.md
├── LICENSE
├── requirements.txt
└── .gitignore

Bước 1: Mở Terminal rồi paste dòng dưới đây để tải những thư viện cần thiết:

pip install -r requirements.txt

Bước 2: Tạo 1 file mới tên là .env ở trong folder backend. Paste dòng dưới đây vào:

GROQ_API_KEY=YOUR_GROQ_API_KEY

Lưu ý 1: .env sẽ bằng cấp với main.py

Lưu ý 2: Dùng Groq để tạo API. Dán API ấy vào chỗ YOUR_GROQ_API_KEY

Bước 3: Copy paste những dòng sau đây:

cd backend
python -m uvicorn main:app --reload --port 8000

Lưu ý QUAN TRỌNG khi chạy lần đầu tiên:
AI đang tự động đóng gói dữ liệu (Chờ từ 10-15 phút):
Vì file dữ liệu phim d1.csv khá nặng, trong lần chạy đầu tiên, Terminal của bạn sẽ hiện thông báo:

✨ Phát hiện chạy dữ liệu d1.csv lần đầu tiên. Tiến hành tiền xử lý...

Lúc này, mô hình AI đang dịch hơn 134k cốt truyện thành ma trận Vector. Tuyệt đối không tắt Terminal. Hãy kiên nhẫn đợi cho đến khi hệ thống hiện chữ:

✅ ĐÃ ĐÓNG GÓI TOÀN BỘ DỮ LIỆU LỚN THÀNH CÔNG!
INFO: Application startup complete.

(Từ lần chạy thứ 2 trở đi, hệ thống sẽ nạp file đã đóng gói mất chưa tới 3 giây).







