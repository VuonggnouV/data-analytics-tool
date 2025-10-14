import os
import random
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog

def draw_pie_from_paths():
    root = Tk()
    root.withdraw()

    DATA_DIR = filedialog.askdirectory(title="Chọn thư mục dữ liệu")
    if not DATA_DIR:
        print("❌ Bạn chưa chọn thư mục nào.")
        return

    classes = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]
    if not classes:
        print("⚠️ Thư mục được chọn không chứa class con nào.")
        return

    counts = [len([f for f in os.listdir(os.path.join(DATA_DIR, d)) 
                   if os.path.isfile(os.path.join(DATA_DIR, d, f))]) for d in classes]

    colors = [(random.random(), random.random(), random.random()) for _ in classes]

    plt.figure(figsize=(8, 8))
    wedges, texts, autotexts = plt.pie(
        counts,
        colors=colors,
        autopct='%1.1f%%',   # hiển thị phần trăm
        startangle=90,       # bắt đầu từ trên cùng
        textprops={'color': 'black', 'fontsize': 10}
    )

    plt.legend(
        wedges,
        [f"{cls} ({count})" for cls, count in zip(classes, counts)],
        title="Class",
        loc="center left",
        bbox_to_anchor=(1, 0.5),
    )

    plt.title("Tỷ lệ số lượng data trong mỗi class", fontsize=14)
    plt.tight_layout()
    plt.show()


draw_pie_from_paths()
