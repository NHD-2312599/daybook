# ĐL-T4 Dashboard

Ứng dụng quản lý điểm danh tổ ĐL-T4

## Tính năng
- Điểm danh 4 mục: **Chép NLSS**, **Nghe Mana**, **Đi Chakki**, **Jondo**
- Tự lưu nháp khi cập nhật trong ngày; có thể tick/bỏ tick và chốt kết quả chính thức cuối ngày
- Cột ghi chú lý do chưa làm
- Suy ngẫm Kinh thánh (copy gửi GYJN)
- Báo cáo tuần của Leader
- Thống kê tổng quan + xuất ảnh PNG
- Lưu dữ liệu trên server (file JSON)

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

## Cấu trúc
```
dl-t4-dashboard/
├── app.py              # Flask backend
├── templates/
│   └── index.html      # Giao diện
├── static/             # (dự phòng)
├── data/               # Dữ liệu JSON (tự tạo khi chạy)
└── README.md
```
