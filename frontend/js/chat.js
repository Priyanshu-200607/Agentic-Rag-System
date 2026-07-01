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
    document.title = `EA - ${username.toUpperCase()}`;
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
            headers: { 'x-username': username },
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
        const response = await fetch(`http://127.0.0.1:8000/history?username=${encodeURIComponent(username)}`);
        const data = await response.json();
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = "";
        
        const accessList = document.getElementById('userAccessList');
        if (accessList && data.allowed) {
            accessList.innerHTML = data.allowed.length > 0 
                ? data.allowed.map(d => `<span class="badge badge-active">${d.toUpperCase()}</span>`).join('') 
                : '<span style="color:#888; font-size:0.9em;">None</span>';
        }
        
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
            // "Clear All" button — only shown to admins
            const clearAllBtn = role === 'admin'
                ? `<button onclick="clearDepartment('${dept}')" style="cursor:pointer; border:none; background:none; color:#c0392b; font-size:0.75em; font-weight:600; padding: 2px 6px; margin-left:8px; border:1px solid #e74c3c; border-radius:4px; vertical-align:middle;" title="Remove ALL files from this department">🗑 Clear All</button>`
                : '';

            let deptHtml = `<details style="margin-bottom: 10px;">
                <summary style="font-weight: bold; color: #444; text-transform: uppercase; font-size: 0.85em; padding: 5px 0; border-bottom: 1px solid #ddd; outline: none; cursor: pointer; user-select: none; display: flex; justify-content: space-between; align-items: center;">
                    <span>📁 ${dept} <span style="color:#888; font-size:0.9em; font-weight:normal; text-transform:none;">(${grouped[dept].length} files)</span></span>
                    ${clearAllBtn}
                </summary>
                <div style="padding-left: 15px; margin-top: 5px;">`;
            
            grouped[dept].forEach(item => {
                const deleteBtn = role === 'admin' 
                    ? `<button onclick="deleteFile('${item.department}', '${item.filename}')" style="cursor:pointer; border:none; background:none; color:red; padding: 0 0 0 10px; flex-shrink: 0;" title="Remove file">❌</button>` 
                    : '';
                    
                deptHtml += `<div style="padding: 6px 0; border-bottom: 1px solid #f0f0f0; font-size: 0.9em; display: flex; justify-content: space-between; align-items: center;">
                    <div style="word-break: break-all; color: #333;">📄 ${item.filename}</div>
                    ${deleteBtn}
                </div>`;
            });
            
            deptHtml += `</div></details>`;
            historyList.innerHTML += deptHtml;
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
    const username = localStorage.getItem('username');
    try {
        const response = await fetch(`http://127.0.0.1:8000/upload/${targetDept}/${filename}`, {
            method: 'DELETE',
            headers: { 'x-username': username }
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

async function clearDepartment(dept) {
    if (!confirm(`⚠️ This will permanently remove ALL documents and knowledge graph data for the "${dept.toUpperCase()}" department.\n\nThis cannot be undone. Are you sure?`)) return;
    const username = localStorage.getItem('username');
    try {
        const response = await fetch(`http://127.0.0.1:8000/upload/${dept}`, {
            method: 'DELETE',
            headers: { 'x-username': username }
        });
        const data = await response.json();
        if (data.status === 'success') {
            loadHistory();
        } else {
            alert('Failed to clear department.');
        }
    } catch (err) {
        alert('Error clearing department.');
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

    const authHeader = { 'x-username': username };

    const deptRes = await fetch('http://127.0.0.1:8000/admin/departments', { headers: authHeader });
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

    const userRes = await fetch('http://127.0.0.1:8000/admin/users', { headers: authHeader });
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
    await fetch(`http://127.0.0.1:8000/admin/departments/${name}`, {
        method: 'POST',
        headers: { 'x-username': username }
    });
    document.getElementById('newDeptInput').value = '';
    loadAdminData();
    populateUploadDropdown();
}

async function populateUploadDropdown() {
    try {
        const deptRes = await fetch('http://127.0.0.1:8000/admin/departments', {
            headers: { 'x-username': username }
        });
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
    await fetch(`http://127.0.0.1:8000/admin/departments/${name}/suspend`, {
        method: 'PUT',
        headers: { 'x-username': username }
    });
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
        headers: { 'Content-Type': 'application/json', 'x-username': username },
        body: JSON.stringify({username: username, password, role: roleVal, allowed_departments: allowed})
    });
    
    // Clear inputs after successful creation
    document.getElementById('newUsername').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('newAccess').value = '';
    
    loadAdminData();
}

async function toggleUserSuspend(targetUser) {
    await fetch(`http://127.0.0.1:8000/admin/users/${targetUser}/suspend`, {
        method: 'PUT',
        headers: { 'x-username': username }
    });
    loadAdminData();
}

async function updateAccess(targetUser) {
    const accessStr = document.getElementById(`acc_${targetUser}`).value.trim();
    let allowed = accessStr ? accessStr.split(',').map(s=>s.trim()) : [];
    await fetch(`http://127.0.0.1:8000/admin/users/${targetUser}/access`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-username': username },
        body: JSON.stringify({allowed_departments: allowed})
    });
    loadAdminData();
}

async function deleteUser(targetUser) {
    if(!confirm(`Delete user ${targetUser}?`)) return;
    await fetch(`http://127.0.0.1:8000/admin/users/${targetUser}`, {
        method: 'DELETE',
        headers: { 'x-username': username }
    });
    loadAdminData();
}
