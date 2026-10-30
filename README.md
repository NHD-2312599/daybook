# To-Do Dashboard

Ứng dụng quản lý lịch trình cá nhân chạy bằng Python Flask, giao diện tiếng Việt và lưu dữ liệu cục bộ bằng SQLite.

## Chạy ứng dụng

1. Cài Python 3.10 trở lên.
2. (Khuyến nghị) Tạo môi trường ảo: `python -m venv .venv` rồi kích hoạt môi trường.
3. Cài thư viện: `pip install -r requirements.txt`.
4. Khởi chạy: `python app.py`.
5. Mở địa chỉ `http://127.0.0.1:5000` trong trình duyệt.

Dữ liệu được lưu trong `instance/todo.db`. Không cần cài hoặc chạy PostgreSQL.

## Chức năng hiện có

- Xem lịch theo ngày, tuần, tháng, quý và năm.
- Tạo sự kiện với giờ bắt đầu/kết thúc, mức ưu tiên, ghi chú và lịch lặp hằng ngày/tuần/tháng.
- Gắn sự kiện vào danh mục Công việc, Cá nhân, Sức khỏe, Học tập hoặc Khác; lọc lịch theo danh mục.
- Đánh dấu hoàn thành riêng cho từng ngày diễn ra sự kiện lặp.
- Xóa sự kiện và xem thống kê tiến độ trong kỳ.
