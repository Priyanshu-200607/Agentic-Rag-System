async function login() {
    const username = document.getElementById('username').value.trim().toLowerCase();
    const password = document.getElementById('password').value.trim();

    const response = await fetch('http://127.0.0.1:8000/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username,
            password
        })
    });

    const data = await response.json();

    if(data.success) {
        localStorage.setItem('username', data.username);
        localStorage.setItem('role', data.role);
        if (data.role === 'admin' || data.role === 'manager') {
            window.location.href = 'admin.html';
        } else {
            window.location.href = 'chat.html';
        }
    } else {
        alert(data.message || "Login failed! Invalid credentials.");
    }
}
