# ai_training/train_ai.py

from ultralytics import YOLO
import os

def main():
    # 1. Chọn model nền (Nano - nhẹ nhất cho CPU)
    # Nó sẽ tự tải về nếu chưa có
    model = YOLO('yolov8n-cls.pt') 

    # 2. Bắt đầu huấn luyện
    # data: trỏ đến thư mục chứa 'train' và 'val'
    # epochs: số lần học lại toàn bộ dữ liệu (30-50 là ổn cho demo)
    # imgsz: kích thước ảnh (224 là chuẩn cho classification)
    print("--- Bắt đầu train ---")
    results = model.train(
        data='./dataset',   # Đường dẫn đến thư mục dataset
        epochs=30,          # Train 30 vòng
        imgsz=224,          # Resize ảnh về 224x224
        device='cpu',       # Dùng CPU (nếu có GPU NVIDIA thì sửa thành '0')
        project='runs',     # Tên thư mục chứa kết quả
        name='monitor_model' # Tên sub-folder kết quả
    )

    # 3. Validate (Kiểm tra độ chính xác sau khi train)
    metrics = model.val()
    
    # 4. In ra đường dẫn file kết quả
    print("\n" + "="*40)
    print("HOÀN TẤT! File model của bạn nằm ở:")
    # Đường dẫn này có thể thay đổi tùy hệ điều hành, hãy nhìn log
    print(os.path.abspath("runs/monitor_model/weights/best.pt"))
    print("="*40)

if __name__ == '__main__':
    main()