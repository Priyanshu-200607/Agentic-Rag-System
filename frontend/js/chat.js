const department = localStorage.getItem('department') || 'hr';

document.addEventListener('DOMContentLoaded', () => {
    if (!localStorage.getItem('department')) {
        window.location.href = 'login.html';
        return;
    }
    
    if (department === 'admin') {
        document.getElementById('adminUploadSection').style.display = 'block';
    }
    
    document.getElementById('deptTitle').innerText = `${department.toUpperCase()} Assistant`;
    document.title = `${department.toUpperCase()} `;
    loadHistory();
});

function handleEnter(event) {
    if (event.key === 'Enter') {
        sendQuestion();
    }
}

async function sendQuestion() {
    const questionInput = document.getElementById('question');
    const question = questionInput.value;
    
    if(!question.trim()) return;

    const div = document.getElementById('messages');
    div.innerHTML += `<p><strong>You:</strong> ${question}</p>`;
    questionInput.value = ""; // clear input
    div.scrollTop = div.scrollHeight;

    const response = await fetch(`http://127.0.0.1:8000/chat/${department}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            question
        })
    });

    const data = await response.json();
    div.innerHTML += `<p><strong>Assistant:</strong> ${data.answer}</p>`;
    div.scrollTop = div.scrollHeight; // auto scroll
}

async function uploadFiles() {
    const fileInput = document.getElementById('fileInput');
    const files = fileInput.files;
    const statusDiv = document.getElementById('uploadStatus');
    const targetDept = document.getElementById('uploadDept').value;
    
    if (files.length === 0) {
        statusDiv.innerText = "Please select files first.";
        statusDiv.style.color = "red";
        return;
    }

    statusDiv.innerText = "Uploading...";
    statusDiv.style.color = "blue";

    const formData = new FormData();
    formData.append("department", targetDept);
    for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
    }

    try {
        const response = await fetch(`http://127.0.0.1:8000/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        if (data.status === "success") {
            statusDiv.innerText = "Upload successful!";
            statusDiv.style.color = "green";
            fileInput.value = ""; // Clear selection
            loadHistory(); // Refresh history
        } else {
            statusDiv.innerText = "Upload failed.";
            statusDiv.style.color = "red";
        }
    } catch (err) {
        statusDiv.innerText = "Error during upload.";
        statusDiv.style.color = "red";
    }
}

async function loadHistory() {
    try {
        const response = await fetch(`http://127.0.0.1:8000/history`);
        const data = await response.json();
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = "";
        
        // Filter history for current department (or show all if admin)
        const filteredHistory = department === 'admin' 
            ? data.history 
            : data.history.filter(item => item.department === department);
            
        // Sort by department alphabetically
        filteredHistory.sort((a, b) => a.department.localeCompare(b.department));
            
        if (filteredHistory.length === 0) {
            historyList.innerHTML = "<p style='color: #666; font-size: 0.9em;'>No files uploaded yet.</p>";
            return;
        }

        const grouped = {};
        filteredHistory.forEach(item => {
            if (!grouped[item.department]) {
                grouped[item.department] = [];
            }
            grouped[item.department].push(item);
        });

        const sortedDepts = Object.keys(grouped).sort();

        sortedDepts.forEach(dept => {
            historyList.innerHTML += `<div style="font-weight: bold; margin-top: 15px; margin-bottom: 5px; color: #444; text-transform: uppercase; font-size: 0.85em; border-bottom: 2px solid #ddd; padding-bottom: 3px;">${dept}</div>`;
            
            grouped[dept].forEach(item => {
                const deleteBtn = department === 'admin' 
                    ? `<button onclick="deleteFile('${item.department}', '${item.filename}')" style="cursor:pointer; border:none; background:none; color:red; padding: 0 0 0 10px; flex-shrink: 0;" title="Remove file">❌</button>` 
                    : '';
                    
                historyList.innerHTML += `<div style="padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 0.9em; display: flex; justify-content: space-between; align-items: center;">
                    <div style="word-break: break-all; color: #333;">📄 ${item.filename}</div>
                    ${deleteBtn}
                </div>`;
            });
        });
    } catch (err) {
        console.error("Failed to load history", err);
    }
}

function logout() {
    localStorage.removeItem('department');
}

async function deleteFile(targetDept, filename) {
    if (!confirm(`Are you sure you want to remove ${filename} from the ${targetDept} database?`)) return;
    
    try {
        const response = await fetch(`http://127.0.0.1:8000/upload/${targetDept}/${filename}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        if (data.status === 'success') {
            loadHistory();
        } else {
            alert("Failed to delete file.");
        }
    } catch (err) {
        alert("Error during deletion.");
    }
}
