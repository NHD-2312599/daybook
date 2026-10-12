# ĐL-T4 Dashboard

Ứng dụng quản lý điểm danh tổ ĐL-T4

## Tính năng
- Điểm danh 4 mục: **Chép NLSS**, **Nghe Mana**, **Đi Chakki**, **Jondo**
- Tự lưu nháp khi cập nhật trong ngày; có thể tick/bỏ tick và chốt kết quả chính thức cuối ngày
- Cột ghi chú lý do chưa làm
- Suy ngẫm Kinh thánh (copy gửi GYJN)
- Báo cáo tuần của Leader
- Thống kê tổng quan + xuất ảnh PNG
- Lưu JSON cục bộ khi chạy local hoặc PostgreSQL khi deploy

## Cách chạy

```bash
# Cài Flask (nếu chưa có)
pip install flask
# hoặc
sudo apt install python3-flask

# Chạy
cd dl-t4-dashboard
python3 app.py
```

Mở trình duyệt: **http://127.0.0.1:5000**

## Deploy lên Vercel

1. Kết nối repository GitHub này với Vercel; Vercel tự nhận diện Flask từ `app.py` và cài thư viện trong `requirements.txt`.
2. Trong Vercel Marketplace, tạo và kết nối một PostgreSQL database (ví dụ Neon) với project. Vercel thường tự thêm `DATABASE_URL`.
3. Nếu nhà cung cấp không tự thêm biến, vào **Settings → Environment Variables** và thêm:
   - **Key:** `DATABASE_URL`
   - **Value:** connection string PostgreSQL do nhà cung cấp cấp (giữ nguyên thông tin đăng nhập; không đưa vào GitHub)
   - **Environments:** Production và Preview
4. Deploy lại sau khi kết nối database/biến môi trường.

App dùng PostgreSQL khi có `DATABASE_URL` hoặc `POSTGRES_URL`; nếu không có thì dùng file JSON cho chạy local. Không cần khai báo `PORT`.

## Cấu trúc
```
dl-t4-dashboard/
├── app.py              # Flask backend
├── requirements.txt    # Thư viện Python cho Vercel
├── templates/
│   └── index.html      # Giao diện
├── static/             # (dự phòng)
├── data/               # Dữ liệu JSON local (không đưa lên GitHub)
└── README.md
```
