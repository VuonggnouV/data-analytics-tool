import os
import random
import io
import base64
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# =====================================================================
# HÀM DÙNG CHUNG ĐỂ ĐẾM FILE TỪ DANH SÁCH ĐƯỜNG DẪN
# =====================================================================
def count_files_from_paths(file_paths):
    class_counts = defaultdict(int)
    if not file_paths:
        return None, "Không có file nào được chọn."

    for path in file_paths:
        parts = path.split('/')
        if len(parts) > 2:
            class_name = parts[1]
            class_counts[class_name] += 1
    
    if not class_counts:
        return None, "Không tìm thấy cấu trúc thư mục class hợp lệ."
        
    return class_counts, None

# char draw
def generate_bar_chart(class_counts):
    classes = list(class_counts.keys())
    counts = list(class_counts.values())
    colors = plt.cm.viridis([random.random() for _ in classes])

    plt.figure(figsize=(10, 6))
    bars = plt.bar(classes, counts, color=colors)
    plt.bar_label(bars, labels=[f"{c}" for c in counts], label_type='edge', padding=3)

    legend_elements = [plt.Rectangle((0, 0), 1, 1, color=color, label=cls) for cls, color in zip(classes, colors)]
    plt.legend(handles=legend_elements, title="Chú thích", bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.title("Số lượng file trong mỗi class")
    plt.xlabel("Class")
    plt.ylabel("Số lượng")
    plt.tight_layout(rect=[0, 0, 0.85, 1])

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return image_base64

# pie draw
def generate_pie_chart(class_counts):
    classes = list(class_counts.keys())
    counts = list(class_counts.values())
    colors = plt.cm.viridis([random.random() for _ in classes])
    
    plt.figure(figsize=(8, 8))
    wedges, _, _ = plt.pie(
        counts,
        colors=colors,
        autopct='%1.1f%%',
        startangle=140,
        textprops={'color': 'white', 'weight': 'bold'}
    )
    
    plt.legend(
        wedges,
        [f"{cls} ({count})" for cls, count in zip(classes, counts)],
        title="Class",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1)
    )

    plt.title("Tỷ lệ file trong mỗi class", fontsize=14)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return image_base64

# route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/draw_chart', methods=['POST'])
def handle_draw_chart():
    """Xử lý cho Tab A (Biểu đồ cột)."""
    data = request.get_json()
    file_paths = data.get('file_paths')
    class_counts, error = count_files_from_paths(file_paths)

    if error:
        return jsonify({"error": error}), 400
    
    image_data = generate_bar_chart(class_counts)
    return jsonify({"image": image_data})

@app.route('/draw_pie_chart', methods=['POST'])
def handle_draw_pie_chart():
    """ROUTE MỚI: Xử lý cho Tab B (Biểu đồ tròn)."""
    data = request.get_json()
    file_paths = data.get('file_paths')
    class_counts, error = count_files_from_paths(file_paths)

    if error:
        return jsonify({"error": error}), 400
    
    image_data = generate_pie_chart(class_counts)
    return jsonify({"image": image_data})

if __name__ == '__main__':
    app.run(debug=True)