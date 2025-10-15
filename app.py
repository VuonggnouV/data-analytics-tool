import os
import io
import time
import base64
import random
import uuid
import json
from collections import defaultdict

# Các thư viện cho phân tích dữ liệu
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import chardet
import ollama

from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)
# Tạo thư mục để lưu các file upload tạm thời
UPLOAD_FOLDER = 'temp_uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# =====================================================================
# LOGIC CHO TAB A & B: BIỂU ĐỒ TỪ THƯ MỤC ẢNH (GIỮ NGUYÊN)
# =====================================================================

def count_files_from_paths(file_paths):
    """Đếm số file trong mỗi thư mục con."""
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

def generate_bar_chart(class_counts):
    """Tạo biểu đồ cột."""
    classes = list(class_counts.keys())
    counts = list(class_counts.values())
    colors = plt.cm.viridis([random.random() for _ in classes])

    plt.figure(figsize=(10, 6))
    bars = plt.bar(classes, counts, color=colors)
    plt.bar_label(bars, labels=[f"{c}" for c in counts], label_type='edge', padding=3)
    plt.title("Số lượng file trong mỗi class")
    plt.xlabel("Class")
    plt.ylabel("Số lượng")
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return image_base64

def generate_pie_chart(class_counts):
    """Tạo biểu đồ tròn."""
    classes = list(class_counts.keys())
    counts = list(class_counts.values())
    colors = plt.cm.viridis([random.random() for _ in classes])
    
    plt.figure(figsize=(8, 8))
    wedges, _, _ = plt.pie(
        counts, colors=colors, autopct='%1.1f%%', startangle=140, 
        textprops={'color': 'white', 'weight': 'bold'}
    )
    plt.legend(
        wedges, [f"{cls} ({count})" for cls, count in zip(classes, counts)],
        title="Class", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1)
    )
    plt.title("Tỷ lệ file trong mỗi class", fontsize=14)
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return image_base64

# =====================================================================
# LOGIC MỚI CHO TAB C: STREAMING PHÂN TÍCH EDA
# =====================================================================

def stream_eda_analysis(session_id):
    """
    Hàm generator chính để stream (luồng) kết quả phân tích EDA.
    """
    file_path = os.path.join(UPLOAD_FOLDER, session_id)
    if not os.path.exists(file_path):
        yield f"data: {json.dumps({'type': 'error', 'message': 'Lỗi: File không tìm thấy trên server.'})}\n\n"
        return

    try:
        # Bước 1: Đọc file dữ liệu
        yield f"data: {json.dumps({'type': 'log', 'message': 'Đang đọc file dữ liệu...'})}\n\n"
        time.sleep(1)
        if file_path.endswith('.csv'):
            with open(file_path, 'rb') as f:
                content = f.read(50000)
            encoding = chardet.detect(content)['encoding'] or 'utf-8'
            df = pd.read_csv(file_path, encoding=encoding)
        else:
            df = pd.read_excel(file_path)
        yield f"data: {json.dumps({'type': 'log', 'message': f'Đọc file thành công. Bắt đầu phân tích...'})}\n\n"

        # Bước 2: Vẽ và stream lần lượt từng biểu đồ
        output_dir_abs = os.path.join('static', 'eda_output', session_id)
        output_dir_rel = os.path.join('eda_output', session_id)
        os.makedirs(output_dir_abs, exist_ok=True)
        
        def plot_and_yield(plot_func, chart_name, file_name, *args):
            """Hàm phụ để vẽ, lưu và gửi sự kiện biểu đồ."""
            try:
                time.sleep(1.5)
                plot_func(*args)
                rel_path = f"/static/{output_dir_rel}/{file_name}.png".replace("\\", "/")
                yield f"data: {json.dumps({'type': 'chart', 'name': chart_name, 'url': rel_path})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'log', 'message': f'Lỗi khi vẽ biểu đồ {chart_name}: {e}'})}\n\n"

        # Vẽ tuần tự 4 biểu đồ
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        if numeric_cols:
            def plot_dist(df_num):
                plt.figure(figsize=(10, 6)); df_num.hist(bins=20, figsize=(10, 6)); plt.suptitle("Phân phối của các cột số")
                plt.tight_layout(rect=[0, 0, 1, 0.95]); plt.savefig(os.path.join(output_dir_abs, "distribution.png")); plt.close()
            yield from plot_and_yield(plot_dist, "Biểu đồ phân phối", "distribution", df[numeric_cols])

            def plot_box(df_num):
                plt.figure(figsize=(10, 6)); sns.boxplot(data=df_num); plt.title("Biểu đồ Boxplot")
                plt.xticks(rotation=45); plt.tight_layout(); plt.savefig(os.path.join(output_dir_abs, "boxplot.png")); plt.close()
            yield from plot_and_yield(plot_box, "Biểu đồ Boxplot", "boxplot", df[numeric_cols])

            def plot_corr(df_num):
                plt.figure(figsize=(10, 8)); corr = df_num.corr(); sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
                plt.title("Ma trận tương quan"); plt.tight_layout(); plt.savefig(os.path.join(output_dir_abs, "correlation.png")); plt.close()
            yield from plot_and_yield(plot_corr, "Ma trận tương quan", "correlation", df[numeric_cols])

        def plot_missing(df_full):
            plt.figure(figsize=(10, 6)); sns.heatmap(df_full.isnull(), cbar=False, cmap="viridis"); plt.title("Biểu đồ các giá trị thiếu")
            plt.tight_layout(); plt.savefig(os.path.join(output_dir_abs, "missing_values.png")); plt.close()
        yield from plot_and_yield(plot_missing, "Biểu đồ giá trị thiếu", "missing_values", df)

        # Bước 3: Gửi tín hiệu bắt đầu AI và stream nhận xét
        yield f"data: {json.dumps({'type': 'start_ai'})}\n\n" # <-- THAY ĐỔI QUAN TRỌNG
        yield f"data: {json.dumps({'type': 'log', 'message': 'Đang sinh nhận xét từ AI...'})}\n\n"
        summary = df.describe(include="all").transpose().fillna("N/A").to_string()
        prompt = f"""
Bạn là chuyên gia phân tích dữ liệu.
Hãy đọc bản tóm tắt sau và viết 8–10 nhận xét toàn bộ bằng tiếng Việt, gồm:
- Các đặc điểm nổi bật
- Xu hướng chính
- Cột nào có giá trị thiếu, ngoại lai, hoặc khác biệt
- Các mối tương quan đáng chú ý
Dataset summary:
{summary}
"""
        stream = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}], stream=True)
        for chunk in stream:
            token = chunk['message']['content']
            yield f"data: {json.dumps({'type': 'ai_token', 'content': token})}\n\n"
            time.sleep(0.02)

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        # Bước 4: Gửi tín hiệu hoàn tất và dọn dẹp
        yield f"data: {json.dumps({'type': 'done', 'message': 'Phân tích hoàn tất!'})}\n\n"
        if os.path.exists(file_path):
            os.remove(file_path)

# =====================================================================
# CÁC ROUTE (ĐIỂM TRUY CẬP API) CỦA FLASK
# =====================================================================
@app.route('/')
def index():
    return render_template('index.html')

# --- API cho Tab A và B ---
@app.route('/draw_chart', methods=['POST'])
def handle_draw_chart():
    data = request.get_json(); file_paths = data.get('file_paths'); class_counts, error = count_files_from_paths(file_paths)
    if error: return jsonify({"error": error}), 400
    image_data = generate_bar_chart(class_counts); time.sleep(2)
    return jsonify({"image": image_data})

@app.route('/draw_pie_chart', methods=['POST'])
def handle_draw_pie_chart():
    data = request.get_json(); file_paths = data.get('file_paths'); class_counts, error = count_files_from_paths(file_paths)
    if error: return jsonify({"error": error}), 400
    image_data = generate_pie_chart(class_counts); time.sleep(2)
    return jsonify({"image": image_data})

# --- API cho Tab C (Streaming) ---
@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    if 'file' not in request.files: return jsonify({"error": "Không có file."}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "Chưa chọn file."}), 400
    session_id = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
    file.save(os.path.join(UPLOAD_FOLDER, session_id))
    return jsonify({"session_id": session_id})

@app.route('/analysis_stream/<session_id>')
def analysis_stream(session_id):
    return Response(stream_eda_analysis(session_id), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)

