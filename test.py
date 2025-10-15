import os
import pandas as pd
import numpy as np
import subprocess
import matplotlib.pyplot as plt
import seaborn as sns
from tkinter import Tk, filedialog
import chardet  # thêm để tự nhận diện mã hóa

# ====== SINH NHẬN XÉT TỪ OLLAMA ======
def generate_insights_ollama(df, model="llama3"):
    import ollama
    summary = df.describe(include="all").transpose().fillna("").to_string()
    prompt = f"""
Bạn là chuyên gia phân tích dữ liệu.
Hãy đọc bản tóm tắt sau và viết 8–10 nhận xét bằng tiếng Việt, gồm:
- Các đặc điểm nổi bật
- Xu hướng chính
- Cột nào có giá trị thiếu, ngoại lai, hoặc khác biệt
- Các mối tương quan đáng chú ý
Dataset summary:
{summary}
"""
    print("🤖 Đang sinh nhận xét  (mất vài giây)...")
    try:
        result = ""
        stream = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            if "message" in chunk:
                text = chunk["message"]["content"]
                print(text, end="", flush=True)
                result += text
        print("\n✅ Hoàn tất nhận xét.")
        return result
    except Exception as e:
        print(f"❌ Lỗi khi gọi Ollama: {e}")
        return "Không thể sinh nhận xét (kiểm tra Ollama đã chạy chưa)."

# ====== VẼ BIỂU ĐỒ ======
def plot_charts(df, out_dir):
    numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
    
    # --- Biểu đồ phân phối ---
    if numeric_cols:
        plt.figure(figsize=(10, 6))
        df[numeric_cols].hist(bins=20, figsize=(10, 6))
        plt.suptitle("Distribution of Numeric Columns", fontsize=14)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(os.path.join(out_dir, "distribution.png"))
        plt.close()
    
        # Boxplot
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=df[numeric_cols])
        plt.title("Boxplot of Numeric Columns")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "boxplot.png"))
        plt.close()
    
        # Correlation heatmap
        plt.figure(figsize=(8, 6))
        corr = df[numeric_cols].corr()
        sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
        plt.title("Correlation Heatmap")
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, "correlation_heatmap.png"))
        plt.close()
    
    else:
        print("⚠️ Không có cột số nào để vẽ biểu đồ.")

    # --- Biểu đồ Missing Values ---
    plt.figure(figsize=(10, 6))
    sns.heatmap(df.isnull(), cbar=False, cmap="viridis")  # NaN = màu sáng, dữ liệu có = màu tối
    plt.title("Missing Values Heatmap")
    plt.xlabel("Columns")
    plt.ylabel("Rows")
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "missing_values_heatmap.png"))
    plt.close()

    print("📊 Đã lưu các biểu đồ vào thư mục output_auto_eda, bao gồm Missing Values Heatmap.")

# ====== PHÂN TÍCH DỮ LIỆU ======
def analyze_data(df):
    print("\n📘 Tổng quan dữ liệu:")
    print(df.info())
    print("\n🔹 5 dòng đầu:")
    print(df.head())
    print("\n🔹 Thống kê mô tả:")
    print(df.describe(include="all"))
    print("\n🔹 Missing values:")
    print(df.isnull().sum())

# ====== HÀM CHÍNH ======
def run_auto_eda_visual_ollama():
    import ollama

    # Kiểm tra Ollama
    try:
        subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
    except Exception:
        print("❌ Chưa cài hoặc chưa khởi động Ollama. Tải tại https://ollama.com/download và đảm bảo nó đang chạy.")
        return

    # Chọn file
    Tk().withdraw()
    file_path = filedialog.askopenfilename(
        title="Chọn file Excel hoặc CSV",
        filetypes=[("Excel/CSV files", "*.xlsx *.xls *.csv")]
    )

    if not file_path:
        print("❌ Không có file được chọn.")
        return

    print(f"📂 File đã chọn: {file_path}")

    # Đọc file
    try:
        if file_path.endswith(".csv"):
            # Tự động phát hiện encoding
            with open(file_path, 'rb') as f:
                result = chardet.detect(f.read(50000))
            encoding = result['encoding'] or 'utf-8'
            print(f"📜 Mã hóa phát hiện: {encoding}")
            df = pd.read_csv(file_path, encoding=encoding)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        print(f"❌ Lỗi khi đọc file: {e}")
        return

    # Phân tích
    analyze_data(df)

    # Tạo thư mục output
    out_dir = os.path.join(os.getcwd(), "output_auto_eda")
    os.makedirs(out_dir, exist_ok=True)

    # Sinh biểu đồ
    plot_charts(df, out_dir)

    # Nhận xét AI
    insights = generate_insights_ollama(df)

    # Lưu nhận xét
    with open(os.path.join(out_dir, "summary.txt"), "w", encoding="utf-8") as f:
        f.write(insights)

    print(f"\n✅ Đã lưu kết quả tại thư mục: {out_dir}")

# ====== CHẠY ======
if __name__ == "__main__":
    run_auto_eda_visual_ollama()
