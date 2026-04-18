<div align="center">
  <img src="farm_icon.png" width="128" />
  <h1>🚀 Microsoft Rewards Farmer Pro</h1>
  <p><b>Hệ thống cày điểm Microsoft Rewards Tự động Toàn diện & Thông minh.</b></p>

  [![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
  [![Selenium](https://img.shields.io/badge/Powered%20by-Selenium-orange.svg)]()
</div>

## ✨ Tính Năng Nổi Bật

- 🤖 **Hoạt Động Ngầm (Daemon):** Tích hợp khay ứng dụng (System Tray). Tự động chạy ẩn đằng sau không chiếm chuột, không bật màn hình gây phiền nhiễu.
- ☁️ **OTA Live Config:** Khắc phục tình trạng "Mù dở dở ương" do bị đổi giao diện. Từ khóa làm nhiệm vụ và Selector nay được tải thẳng từ kho mạng, cập nhật 1 giây không cần compile lại app.
- 🎯 **Anti-Lost & Flyout Sniper:** Tự động chui vào các Menu Ẩn (Medal Flyout) để vét sạch từng điểm cuối cùng. Đứt gánh giữa chừng? Tự reload, có lỗi bỏ qua chuyển thẳng tab khác. 
- 🔗 **Tích hợp Affiliate:** Hỗ trợ nhúng link Affiliate đa dạng xoay tua mỗi khi app được kích hoạt.
- 📊 **Theo Dõi Bằng Bảng Mạch:** Giao diện điều khiển (GUI) có thể mở lên để dễ dàng theo dõi chi tiết % tiến độ.

## 📦 Cài Đặt Khởi Tạo

Bạn cần phải cài đặt **Python 3.10+** trở lên. Chú ý kích chọn `Add Python to PATH` trong lúc cài màn hình đầu.

1. **Clone repository này về:**
   ```bash
   git clone https://github.com/huyhoangnp11-afk/MSRFarmer.git
   cd MSRFarmer
   ```

2. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Hướng Dẫn Sử Dụng

Sau khi setup xong, cách đơn giản nhất để khởi chạy ứng dụng là đúp chuột mở file:
**👉 `MSR_Smart_Launcher.py`**

Chương trình sẽ âm thầm chạy xuống Taskbar góc góc phải màn hình của bạn. 
* Kích đúp vào Icon chiếc lá màu xanh để mở lên Bảng điều khiển Console vặn thông số.
* Nhấp phải chuột để chọn **Khởi động cùng Windows** và **Auto Treo Máy**.

## 🛠 Cách Dùng Cơ Chế OTA (Chi Dành Cho Admin)

Bot dùng 1 JSON List để quét các thẻ công việc. 
Truy cập vào file `farm/ota.py` và dán Link Github Gist (Raw) có dạng như dưới đây để ép ứng dụng bú cấu hình mạng:

```json
{
    "keywords": [
        "quote", "quiz", "puzzle", "answer", "poll"
    ],
    "affiliate_links": [
        "https://s.shopee.vn/xxx"
    ]
}
```

## ⚠️ Lưu Ý:
Tool được xây dựng với mục đích tối ưu hóa trải nghiệm sử dụng cá nhân và học tập kiến trúc mã nguồn mở. Việc bạn farm quá liều vượt rào Policy của Microsoft là lỗi do bạn! Hãy sử dụng một cách điều độ!
