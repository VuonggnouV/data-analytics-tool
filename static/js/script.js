// Lấy các phần tử DOM cần thiết
const tabs = document.querySelectorAll(".tab");
const contents = document.querySelectorAll(".tab-content");
const folderInput = document.getElementById("folder");

// Xử lý chuyển tab
tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    tabs.forEach(t => t.classList.remove("active"));
    contents.forEach(c => c.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(tab.dataset.tab).classList.add("active");
  });
});

/**
 * Hàm chung để tạo và hiển thị biểu đồ
 * @param {string} endpoint - URL của API trên server
 * @param {string} chartAreaId - ID của div để hiển thị kết quả
 */
async function generateChart(endpoint, chartAreaId) {
  const chartArea = document.getElementById(chartAreaId);
  
  // Hiển thị hiệu ứng skeleton loading
  chartArea.innerHTML = '<div class="skeleton"></div>';

  if (!folderInput.files.length) {
    chartArea.innerHTML = `<p class="error-message">⚠️ Vui lòng chọn thư mục trước!</p>`;
    return;
  }

  const filePaths = Array.from(folderInput.files).map(file => file.webkitRelativePath);

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ file_paths: filePaths })
    });

    const data = await res.json();
    if (res.ok) {
      chartArea.innerHTML = `<img src="data:image/png;base64,${data.image}" alt="Biểu đồ">`;
    } else {
      chartArea.innerHTML = `<p class="error-message">❌ ${data.error || 'Đã có lỗi xảy ra.'}</p>`;
    }
  } catch (error) {
    chartArea.innerHTML = `<p class="error-message">❌ Lỗi kết nối đến server: ${error.message}</p>`;
  }
}

// Gắn sự kiện cho các nút
document.getElementById("draw-bar-btn").addEventListener("click", () => {
  generateChart('/draw_chart', 'bar-chart-area');
});

document.getElementById("draw-pie-btn").addEventListener("click", () => {
  generateChart('/draw_pie_chart', 'pie-chart-area');
});