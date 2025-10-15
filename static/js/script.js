// Lấy các phần tử DOM
const tabs = document.querySelectorAll(".tab");
const contents = document.querySelectorAll(".tab-content");
const folderInput = document.getElementById("folder-input");
const dataFileInput = document.getElementById("data-file-input");

// Xử lý chuyển tab (giữ nguyên)
tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    contents.forEach(c => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab).classList.add("active");
  });
});

// Hàm cho Tab A và B (giữ nguyên)
async function generateChartFromFolder(endpoint, chartAreaId) {
    const chartArea = document.getElementById(chartAreaId);
    chartArea.innerHTML = '<div class="skeleton"></div>';
    if (!folderInput.files.length) {
        chartArea.innerHTML = `<p class="error-message">⚠️ Vui lòng chọn thư mục ảnh trước!</p>`;
        return;
    }
    const filePaths = Array.from(folderInput.files).map(file => file.webkitRelativePath);
    try {
        const res = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ file_paths: filePaths }) });
        const data = await res.json();
        if (res.ok) chartArea.innerHTML = `<img src="data:image/png;base64,${data.image}" alt="Biểu đồ">`;
        else chartArea.innerHTML = `<p class="error-message">❌ ${data.error || 'Lỗi.'}</p>`;
    } catch (error) {
        chartArea.innerHTML = `<p class="error-message">❌ Lỗi kết nối: ${error.message}</p>`;
    }
}
document.getElementById("draw-bar-btn").addEventListener("click", () => generateChartFromFolder('/draw_chart', 'bar-chart-area'));
document.getElementById("draw-pie-btn").addEventListener("click", () => generateChartFromFolder('/draw_pie_chart', 'pie-chart-area'));

// LOGIC CHO TAB C (STREAMING)
document.getElementById("analyze-btn").addEventListener("click", async () => {
    const resultsArea = document.getElementById("eda-results-area");
    if (!dataFileInput.files.length) {
        resultsArea.innerHTML = `<p class="error-message">⚠️ Vui lòng chọn tệp dữ liệu trước!</p>`;
        return;
    }

    resultsArea.innerHTML = `
        <div id="eda-log" class="eda-log"><p>Đang tải tệp lên và chuẩn bị phân tích...</p></div>
        <h3>Các biểu đồ trực quan</h3>
        <div id="eda-charts-stream" class="eda-charts-container"></div>
        <div id="ai-section" style="display: none;">
            <h3>Nhận xét từ AI</h3>
            <div id="ai-insights-stream" class="ai-insights"></div>
        </div>`;
        
    const file = dataFileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    const startRes = await fetch('/start_analysis', { method: 'POST', body: formData });
    const startData = await startRes.json();

    if (!startRes.ok) {
        resultsArea.innerHTML = `<p class="error-message">❌ Lỗi khi bắt đầu phân tích: ${startData.error}</p>`;
        return;
    }

    const logArea = document.getElementById('eda-log');
    logArea.innerHTML = "";
    const chartsArea = document.getElementById('eda-charts-stream');
    const aiSection = document.getElementById('ai-section');
    const insightsArea = document.getElementById('ai-insights-stream');

    const evtSource = new EventSource(`/analysis_stream/${startData.session_id}`);
    
    // --- THAY ĐỔI 1: Thêm biến cờ để theo dõi token đầu tiên của AI
    let isFirstAiToken = true;

    evtSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        switch (data.type) {
            case 'log':
                logArea.innerHTML += `<p>${data.message}</p>`;
                break;
            
            case 'chart':
                const chartId = `chart-${data.name.replace(/\s/g, '-')}`;
                const chartContainer = document.createElement('div');
                chartContainer.id = `${chartId}-container`;
                chartContainer.innerHTML = `
                    <h4>${data.name}</h4>
                    <div class="skeleton"></div>`;
                chartsArea.appendChild(chartContainer);
                
                const img = new Image();
                img.src = `${data.url}?t=${new Date().getTime()}`;

                img.onload = function() {
                    setTimeout(() => {
                        const containerToUpdate = document.getElementById(`${chartId}-container`);
                        if (containerToUpdate) {
                            containerToUpdate.innerHTML = `<h4>${data.name}</h4><img src="${img.src}" alt="${data.name} chart">`;
                        }
                    }, 300);
                };
                break;
            
            // --- THAY ĐỔI 2: Cập nhật logic cho 'start_ai' và 'ai_token'
            case 'start_ai':
                aiSection.style.display = 'block';
                // Hiển thị skeleton text
                insightsArea.innerHTML = `
                    <div class="skeleton-text w-100"></div>
                    <div class="skeleton-text w-90"></div>
                    <div class="skeleton-text w-70"></div>
                `;
                break;

            case 'ai_token':
                // Nếu là token đầu tiên, hãy xóa skeleton trước
                if (isFirstAiToken) {
                    insightsArea.innerHTML = '';
                    isFirstAiToken = false;
                }
                // Sau đó bắt đầu nối chuỗi
                insightsArea.innerHTML += data.content;
                break;
            // --- Kết thúc thay đổi ---

            case 'error':
                logArea.innerHTML += `<p class="error-message">❌ Lỗi: ${data.message}</p>`;
                evtSource.close();
                break;
            case 'done':
                logArea.innerHTML += `<p>✅ ${data.message}</p>`;
                evtSource.close();
                break;
        }
    };

    evtSource.onerror = function(err) {
        logArea.innerHTML += `<p class="error-message">❌ Mất kết nối đến server.</p>`;
        evtSource.close();
    };
});