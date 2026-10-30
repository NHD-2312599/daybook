# To-Do Dashboard

Ứng dụng quản lý lịch trình cá nhân chạy bằng Python Flask, giao diện tiếng Việt. Khi chạy local, dữ liệu được lưu bằng SQLite; khi deploy, app dùng PostgreSQL nếu có biến kết nối.

## Chạy ứng dụng

1. Cài Python 3.10 trở lên.
2. (Khuyến nghị) Tạo môi trường ảo: `python -m venv .venv` rồi kích hoạt môi trường.
3. Cài thư viện: `pip install -r requirements.txt`.
4. Khởi chạy: `python app.py`.
5. Mở địa chỉ `http://127.0.0.1:5000` trong trình duyệt.

Dữ liệu local được lưu trong `instance/todo.db`.

## Deploy lên Vercel với Neon

1. Kết nối Neon với project Vercel và bật biến `DATABASE_URL` (hoặc `DATABASE_URL_UNPOOLED`) cho Production và Preview.
2. Đảm bảo các biến đã được thêm vào đúng project Vercel.
3. Redeploy sau khi thêm biến. App sẽ tự tạo các bảng PostgreSQL khi khởi động.

Vercel không giữ file SQLite trong thư mục ứng dụng; Neon PostgreSQL được dùng để lưu dữ liệu bền vững khi biến kết nối có mặt.

## Chức năng hiện có

- Xem lịch theo ngày, tuần, tháng, quý và năm.
- Tạo sự kiện với giờ bắt đầu/kết thúc, mức ưu tiên, ghi chú và lịch lặp hằng ngày/tuần/tháng.
- Gắn sự kiện vào danh mục Công việc, Cá nhân, Sức khỏe, Học tập hoặc Khác; lọc lịch theo danh mục.
- Đánh dấu hoàn thành riêng cho từng ngày diễn ra sự kiện lặp.
- Xóa sự kiện và xem thống kê tiến độ trong kỳ.
