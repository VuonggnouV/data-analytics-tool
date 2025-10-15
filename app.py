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
from flask_caching import Cache

app = Flask(__name__)

# Cấu hình cache cho ứng dụng
config = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300 
}
app.config.from_mapping(config)
cache = Cache(app)

# =====================================================================
# LOGIC CHO TAB A & B: BIỂU ĐỒ TỪ THƯ MỤC ẢNH (GIỮ NGUYÊN)
# =====================================================================
# Lưu ý: Phần này vẫn dùng file và base64, logic không đổi
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

def generate_bar_chart(class_counts):
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
# LOGIC MỚI CHO TAB C: STREAMING EDA HOÀN TOÀN TRONG BỘ NHỚ
# =====================================================================

def stream_eda_analysis(session_id):
    cached_data = cache.get(session_id)
    if not cached_data:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Lỗi: Phiên làm việc đã hết hạn hoặc không tồn tại.'})}\n\n"
        return

    filename, file_content = cached_data

    try:
        yield f"data: {json.dumps({'type': 'log', 'message': 'Đang đọc dữ liệu từ bộ nhớ...'})}\n\n"
        time.sleep(1)
        file_stream = io.BytesIO(file_content)
        if filename.lower().endswith('.csv'):
            encoding = chardet.detect(file_content[:50000])['encoding'] or 'utf-8'
            df = pd.read_csv(file_stream, encoding=encoding)
        else:
            df = pd.read_excel(file_stream)
        yield f"data: {json.dumps({'type': 'log', 'message': f'Đọc dữ liệu thành công. Bắt đầu phân tích...'})}\n\n"

        # --- THAY ĐỔI 1: Hàm vẽ và yield biểu đồ trực tiếp từ bộ nhớ ---
        def plot_and_yield(plot_func, chart_name, *args):
            try:
                time.sleep(1.5)
                # 1. Hàm vẽ bây giờ trả về một buffer chứa dữ liệu ảnh
                image_buffer = plot_func(*args)
                # 2. Mã hóa buffer thành chuỗi Base64
                image_base64 = base64.b64encode(image_buffer.read()).decode('utf-8')
                # 3. Tạo Data URL để trình duyệt có thể hiển thị trực tiếp
                data_url = f"data:image/png;base64,{image_base64}"
                # 4. Gửi Data URL về client (vẫn dùng key 'url' để script.js tương thích)
                yield f"data: {json.dumps({'type': 'chart', 'name': chart_name, 'url': data_url})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'log', 'message': f'Lỗi khi vẽ biểu đồ {chart_name}: {e}'})}\n\n"
        
        # --- THAY ĐỔI 2: Các hàm vẽ biểu đồ trả về buffer thay vì lưu file ---
        def plot_dist(df_num):
            plt.figure(figsize=(10, 6)); df_num.hist(bins=20, figsize=(10, 6)); plt.suptitle("Phân phối của các cột số")
            plt.tight_layout(rect=[0, 0, 1, 0.95])
            buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close(); buf.seek(0)
            return buf

        def plot_box(df_num):
            plt.figure(figsize=(10, 6)); sns.boxplot(data=df_num); plt.title("Biểu đồ Boxplot")
            plt.xticks(rotation=45); plt.tight_layout()
            buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close(); buf.seek(0)
            return buf

        def plot_corr(df_num):
            plt.figure(figsize=(10, 8)); corr = df_num.corr(); sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
            plt.title("Ma trận tương quan"); plt.tight_layout()
            buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close(); buf.seek(0)
            return buf

        def plot_missing(df_full):
            plt.figure(figsize=(10, 6)); sns.heatmap(df_full.isnull(), cbar=False, cmap="viridis"); plt.title("Biểu đồ các giá trị thiếu")
            plt.tight_layout()
            buf = io.BytesIO(); plt.savefig(buf, format='png'); plt.close(); buf.seek(0)
            return buf

        # --- THAY ĐỔI 3: Cập nhật các lệnh gọi hàm `plot_and_yield` ---
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        if numeric_cols:
            yield from plot_and_yield(plot_dist, "Biểu đồ phân phối", df[numeric_cols])
            yield from plot_and_yield(plot_box, "Biểu đồ Boxplot", df[numeric_cols])
            yield from plot_and_yield(plot_corr, "Ma trận tương quan", df[numeric_cols])

        yield from plot_and_yield(plot_missing, "Biểu đồ giá trị thiếu", df)

        # Phần gọi AI giữ nguyên
        yield f"data: {json.dumps({'type': 'log', 'message': 'Đang chuẩn bị dữ liệu cho AI...'})}\n\n"
        summary = df.describe(include="all").transpose().fillna("N/A").to_string()
        prompt = f"""
Bạn là chuyên gia phân tích dữ liệu.
Hãy đọc bản tóm tắt sau và viết 8–10 nhận xét bằng tiếng Việt, gồm:
- Các đặc điểm nổi bật
- Xu hướng chính
- Cột nào có giá trị thiếu, ngoại lai, hoặc khác biệt
- Các mối tương quan đáng chú ý
Trả lời toàn bộ bằng tiếng Việt Nam.
{summary}
"""
        yield f"data: {json.dumps({'type': 'start_ai'})}\n\n" 
        yield f"data: {json.dumps({'type': 'log', 'message': 'Đang sinh nhận xét từ AI...'})}\n\n"
        
        stream = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}], stream=True)
        for chunk in stream:
            token = chunk['message']['content']
            yield f"data: {json.dumps({'type': 'ai_token', 'content': token})}\n\n"
            time.sleep(0.02)

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        cache.delete(session_id)
        yield f"data: {json.dumps({'type': 'done', 'message': 'Phân tích hoàn tất!'})}\n\n"


# =====================================================================
# CÁC ROUTE (ĐIỂM TRUY CẬP API) CỦA FLASK
# =====================================================================
@app.route('/')
def index():
    return render_template('index.html')

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

@app.route('/start_analysis', methods=['POST'])
def start_analysis():
    if 'file' not in request.files: return jsonify({"error": "Không có file."}), 400
    file = request.files['file']
    if file.filename == '': return jsonify({"error": "Chưa chọn file."}), 400
    
    file_content = file.read()
    session_id = str(uuid.uuid4())
    cache.set(session_id, (file.filename, file_content))
    
    return jsonify({"session_id": session_id})

@app.route('/analysis_stream/<session_id>')
def analysis_stream(session_id):
    return Response(stream_eda_analysis(session_id), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)