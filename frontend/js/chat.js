const role = localStorage.getItem('role') || 'employee';
const username = localStorage.getItem('username');

document.addEventListener('DOMContentLoaded', () => {
    if (!username) {
        window.location.href = 'login.html';
        return;
    }
    
    if (role === 'admin') {
        document.getElementById('adminUploadSection').style.display = 'block';
        document.getElementById('adminNavSection').style.display = 'block';
        loadAdminData();
        populateUploadDropdown();
    }
    
    document.getElementById('deptTitle').innerText = `Workspace (Role: ${role.toUpperCase()})`;
    document.title = `Enterprise Assistant`;
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
    questionInput.value = ""; 
    div.scrollTop = div.scrollHeight;

    try {
        const response = await fetch(`http://127.0.0.1:8000/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, username })
        });

        const data = await response.json();
        div.innerHTML += `<p><strong>Assistant:</strong> ${data.answer}</p>`;
        div.scrollTop = div.scrollHeight;
    } catch(e) {
        div.innerHTML += `<p style="color:red;"><strong>Error:</strong> Failed to connect to server.</p>`;
        div.scrollTop = div.scrollHeight;
    }
}

async function uploadFiles() {
    const fileInput = document.getElementById('fileInput');
    const files = fileInput.files;
    const statusDiv = document.getElementById('uploadStatus');
    const targetDept = document.getElementById('uploadDept').value.trim();
    
    if (files.length === 0 || !targetDept) {
        statusDiv.innerText = "Please select files and enter department.";
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
            fileInput.value = ""; 
            loadHistory();
            loadAdminData();
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
        
        let filteredHistory = data.history;
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
                const deleteBtn = role === 'admin' 
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
    localStorage.removeItem('username');
    localStorage.removeItem('role');
}

async function deleteFile(targetDept, filename) {
    if (!confirm(`Are you sure you want to remove ${filename} from the ${targetDept} database?`)) return;
    
    try {
        const response = await fetch(`http://127.0.0.1:8000/upload/${targetDept}/${filename}`, { method: 'DELETE' });
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

// --- Navigation Logic ---
function showChat() {
    document.getElementById('chatPanel').classList.add('active');
    document.getElementById('adminPanel').classList.remove('active');
    document.getElementById('navChatBtn').classList.add('active');
    document.getElementById('navAdminBtn').classList.remove('active');
}

function showDashboard() {
    document.getElementById('chatPanel').classList.remove('active');
    document.getElementById('adminPanel').classList.add('active');
    document.getElementById('navChatBtn').classList.remove('active');
    document.getElementById('navAdminBtn').classList.add('active');
    loadAdminData();
}

// --- Admin Dashboard Logic ---
async function loadAdminData() {
    if(role !== 'admin') return;

    const deptRes = await fetch('http://127.0.0.1:8000/admin/departments');
    const departments = await deptRes.json();
    const deptBody = document.getElementById('deptTableBody');
    deptBody.innerHTML = '';
    for(let d in departments) {
        let status = departments[d].status;
        let isActive = status === 'active';
        deptBody.innerHTML += `<tr>
            <td>${d}</td>
            <td><span class="badge ${isActive ? 'badge-active' : 'badge-suspended'}">${status}</span></td>
            <td><button class="modal-btn ${isActive ? 'modal-btn-warning' : 'modal-btn-success'}" onclick="toggleDeptSuspend('${d}')">${isActive ? 'Suspend' : 'Activate'}</button></td>
        </tr>`;
    }

    const userRes = await fetch('http://127.0.0.1:8000/admin/users');
    const users = await userRes.json();
    const userBody = document.getElementById('usersTableBody');
    userBody.innerHTML = '';
    for(let u in users) {
        let status = users[u].status || 'active';
        let isActive = status === 'active';
        userBody.innerHTML += `<tr>
            <td><strong>${u}</strong></td>
            <td>${users[u].role}</td>
            <td>
                <div class="access-cell">
                    <input id="acc_${u}" value="${(users[u].allowed_departments || []).join(',')}">
                    <button class="modal-btn modal-btn-info" onclick="updateAccess('${u}')">Save</button>
                </div>
            </td>
            <td><span class="badge ${isActive ? 'badge-active' : 'badge-suspended'}">${status}</span></td>
            <td>
                <div class="action-cell">
                    <button class="modal-btn ${isActive ? 'modal-btn-warning' : 'modal-btn-success'}" onclick="toggleUserSuspend('${u}')">${isActive ? 'Suspend' : 'Activate'}</button>
                    <button class="modal-btn modal-btn-danger" onclick="deleteUser('${u}')">Delete</button>
                </div>
            </td>
        </tr>`;
    }
}

async function addDepartment() {
    const name = document.getElementById('newDeptInput').value.trim();
    if(!name) return;
    await fetch(`http://127.0.0.1:8000/admin/departments/${name}`, {method: 'POST'});
    document.getElementById('newDeptInput').value = '';
    loadAdminData();
    populateUploadDropdown();
}

async function populateUploadDropdown() {
    try {
        const deptRes = await fetch('http://127.0.0.1:8000/admin/departments');
        const departments = await deptRes.json();
        const select = document.getElementById('uploadDept');
        select.innerHTML = '<option value="" disabled selected>Select Department...</option>';
        for(let d in departments) {
            select.innerHTML += `<option value="${d}">${d.toUpperCase()}</option>`;
        }
    } catch(e) {
        console.error("Failed to load departments", e);
    }
}

async function toggleDeptSuspend(name) {
    await fetch(`http://127.0.0.1:8000/admin/departments/${name}/suspend`, {method: 'PUT'});
    loadAdminData();
}

async function addUser() {
    const username = document.getElementById('newUsername').value.trim();
    const password = document.getElementById('newPassword').value.trim();
    const roleVal = document.getElementById('newRole').value;
    const accessStr = document.getElementById('newAccess').value.trim();
    if(!username || !password) return alert("Username and password required");
    
    let allowed = accessStr ? accessStr.split(',').map(s=>s.trim()) : [];
    
    await fetch(`http://127.0.0.1:8000/admin/users`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username, password, role: roleVal, allowed_departments: allowed})
    });
    
    // Clear inputs after successful creation
    document.getElementById('newUsername').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('newAccess').value = '';
    
    loadAdminData();
}

async function toggleUserSuspend(username) {
    await fetch(`http://127.0.0.1:8000/admin/users/${username}/suspend`, {method: 'PUT'});
    loadAdminData();
}

async function updateAccess(username) {
    const accessStr = document.getElementById(`acc_${username}`).value.trim();
    let allowed = accessStr ? accessStr.split(',').map(s=>s.trim()) : [];
    await fetch(`http://127.0.0.1:8000/admin/users/${username}/access`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({allowed_departments: allowed})
    });
    // Removed the annoying alert() pop-up; it just updates cleanly
    loadAdminData();
}

async function deleteUser(username) {
    if(!confirm(`Delete user ${username}?`)) return;
    await fetch(`http://127.0.0.1:8000/admin/users/${username}`, {method: 'DELETE'});
    loadAdminData();
}
