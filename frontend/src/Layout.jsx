import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";

const Layout = ({ children, activeTab }) => {
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("");
  const [departments, setDepartments] = useState({});
  const [uploadDept, setUploadDept] = useState("");
  const [files, setFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState("");
  const [uploadStatusColor, setUploadStatusColor] = useState("");
  const [access, setAccess] = useState([]);
  const [history, setHistory] = useState([]);

  const navigate = useNavigate();

  useEffect(() => {
    const user = localStorage.getItem("username");
    const userRole = localStorage.getItem("role") || "employee";
    if (!user) {
      navigate("/login");
      return;
    }
    setUsername(user);
    setRole(userRole);
    loadHistory(user);
    if (userRole === "admin") {
      loadDepartments(user);
    }
  }, [navigate]);

  const loadHistory = async (user) => {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/history?username=${encodeURIComponent(user)}`,
      );
      const data = await response.json();
      setAccess(data.allowed || []);
      setHistory(data.history || []);
    } catch (e) {
      console.error(e);
    }
  };

  const loadDepartments = async (user) => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/admin/departments?t=${Date.now()}`,
        {
          headers: { "x-username": user },
        },
      );
      const data = await res.json();
      setDepartments(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    navigate("/login");
  };

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
    setUploadStatus("");
  };

  const handleUpload = async () => {
    if (!uploadDept) {
      setUploadStatus("Please select a department.");
      setUploadStatusColor("text-error");
      return;
    }
    if (files.length === 0) {
      setUploadStatus("Please select files.");
      setUploadStatusColor("text-error");
      return;
    }

    setUploadStatus("Uploading...");
    setUploadStatusColor("text-primary");

    const formData = new FormData();
    formData.append("department", uploadDept);
    files.forEach((f) => formData.append("files", f));

    try {
      const res = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        headers: { "x-username": username },
        body: formData,
      });
      const data = await res.json();
      if (data.status === "success") {
        setUploadStatus("Upload successful!");
        setUploadStatusColor("text-success");
        setFiles([]);
        const fileInput = document.getElementById("file-upload");
        if (fileInput) fileInput.value = "";
        loadHistory(username);
      } else {
        setUploadStatus("Upload failed.");
        setUploadStatusColor("text-error");
      }
    } catch (e) {
      setUploadStatus("Error connecting to server.");
      setUploadStatusColor("text-error");
    }
  };

  const deleteFile = async (dept, filename) => {
    if (!window.confirm(`Remove ${filename} from ${dept}?`)) return;
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/upload/${dept}/${filename}`,
        {
          method: "DELETE",
          headers: { "x-username": username },
        },
      );
      const data = await response.json();
      if (data.status === "success") loadHistory(username);
    } catch (err) {
      alert("Error deleting file.");
    }
  };

  const clearDepartment = async (event, dept) => {
    event.preventDefault();
    if (!window.confirm(`Clear all files from ${dept}?`)) return;
    try {
      const response = await fetch(`http://127.0.0.1:8000/upload/${dept}`, {
        method: "DELETE",
        headers: { "x-username": username },
      });
      const data = await response.json();
      if (data.status === "success") loadHistory(username);
    } catch (err) {
      alert("Error clearing department.");
    }
  };

  // Group history by department
  const groupedHistory = history.reduce((acc, item) => {
    if (!acc[item.department]) acc[item.department] = [];
    acc[item.department].push(item);
    return acc;
  }, {});

  return (
    <div className="flex min-h-screen bg-background text-on-background font-body-md">
      {/* Side Navigation Shell */}
      <aside className="flex flex-col h-screen w-64 fixed left-0 top-0 bg-surface-container/90 backdrop-blur-xl border-r border-outline-variant/30 py-6 px-4 z-20">
        <div className="mb-8 px-2">
          <div className="font-headline-md text-headline-md font-bold text-primary flex items-center gap-2">
            <span
              className="material-symbols-outlined"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              terminal
            </span>
            MSFC RAG
          </div>
          <div className="text-on-surface-variant font-label-md text-sm mt-1">
            Intelligence Engine
          </div>
        </div>

        <div className="space-y-1 custom-scrollbar overflow-y-auto flex-1">
          <div className="text-on-surface-variant font-label-md text-xs uppercase tracking-wider mb-2 px-2">
            Menu
          </div>
          <Link
            to="/chat"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:bg-surface-container-highest transition-colors font-body-md ${activeTab === "chat" ? "text-primary font-bold border-r-2 border-primary bg-primary-fixed/30" : ""}`}
          >
            <span className="material-symbols-outlined">chat</span>
            Chat
          </Link>
          {role === "admin" && (
            <Link
              to="/admin"
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:bg-surface-container-highest transition-colors font-body-md ${activeTab === "admin" ? "text-primary font-bold border-r-2 border-primary bg-primary-fixed/30" : ""}`}
            >
              <span
                className="material-symbols-outlined"
                style={{
                  fontVariationSettings:
                    activeTab === "admin" ? "'FILL' 1" : "",
                }}
              >
                dashboard
              </span>
              Admin Dashboard
            </Link>
          )}

          {role === "admin" && (
            <div className="mt-8 px-2">
              <div className="text-on-surface-variant font-label-md text-xs uppercase tracking-wider mb-2">
                Upload Files
              </div>
              <select
                value={uploadDept}
                onChange={(e) => setUploadDept(e.target.value)}
                className="w-full bg-white border border-outline-variant rounded-lg p-2 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none mb-3"
              >
                <option value="" disabled>
                  Select Department...
                </option>
                {Object.keys(departments)
                  .filter((d) => departments[d].status === "active")
                  .map((d) => (
                    <option key={d} value={d}>
                      {d.toUpperCase()}
                    </option>
                  ))}
              </select>
              <div className="border-2 border-dashed border-outline-variant/50 rounded-lg p-3 text-center mb-4 hover:border-primary transition-colors cursor-pointer relative">
                <input
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  id="file-upload"
                  type="file"
                  multiple
                  onChange={handleFileChange}
                />
                <div className="pointer-events-none">
                  <span className="material-symbols-outlined text-outline text-3xl mb-1">
                    cloud_upload
                  </span>
                  <p className="text-xs text-on-surface-variant">
                    {files.length > 0
                      ? `${files.length} file(s) selected`
                      : "Browse or drag files"}
                  </p>
                </div>
              </div>
              {uploadStatus && (
                <div
                  className={`text-xs mb-2 text-center ${uploadStatusColor}`}
                >
                  {uploadStatus}
                </div>
              )}
              <button
                onClick={handleUpload}
                className="w-full bg-success text-white py-2 rounded-lg font-label-md flex items-center justify-center gap-2 hover:opacity-90 transition-opacity"
              >
                <span className="material-symbols-outlined text-sm">
                  upload
                </span>
                Upload
              </button>
            </div>
          )}

          <div className="mt-8 px-2">
            <div className="text-on-surface-variant font-label-md text-xs uppercase tracking-wider mb-2">
              My Access
            </div>
            <div className="flex flex-wrap gap-2">
              {access.length > 0 ? (
                access.map((d) => (
                  <span
                    key={d}
                    className="px-2 py-1 bg-secondary-container text-on-secondary-container rounded text-[10px] font-bold"
                  >
                    {d.toUpperCase()}
                  </span>
                ))
              ) : (
                <span className="text-xs text-on-surface-variant">None</span>
              )}
            </div>
          </div>

          <div className="mt-8 px-2">
            <div className="text-on-surface-variant font-label-md text-xs uppercase tracking-wider mb-2">
              Upload History
            </div>
            <div className="space-y-2">
              {Object.keys(groupedHistory).length === 0 ? (
                <p className="text-xs text-on-surface-variant px-2">
                  No files uploaded yet.
                </p>
              ) : (
                Object.keys(groupedHistory).map((dept) => (
                  <details
                    key={dept}
                    className="bg-white/50 rounded-lg border border-outline-variant/20 overflow-hidden group"
                  >
                    <summary className="flex justify-between items-center p-2 cursor-pointer list-none hover:bg-surface-container-low transition-colors">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-warning text-sm group-open:rotate-90 transition-transform">
                          chevron_right
                        </span>
                        <span className="text-xs font-medium uppercase">
                          {dept}{" "}
                          <span className="text-on-surface-variant opacity-60">
                            ({groupedHistory[dept].length})
                          </span>
                        </span>
                      </div>
                      {role === "admin" && (
                        <button
                          onClick={(e) => clearDepartment(e, dept)}
                          className="text-[10px] text-error font-bold border border-error/20 px-1 rounded hover:bg-error-container shrink-0"
                        >
                          Clear
                        </button>
                      )}
                    </summary>
                    <div className="px-3 pb-2 pt-1 bg-surface-container-lowest/50">
                      {groupedHistory[dept].map((f) => (
                        <div
                          key={f.filename}
                          className="flex justify-between items-center py-1.5 border-b border-outline-variant/10 last:border-0"
                        >
                          <span
                            className="text-[11px] text-on-surface truncate pr-2"
                            title={f.filename}
                          >
                            📄 {f.filename}
                          </span>
                          {role === "admin" && (
                            <button
                              onClick={() => deleteFile(dept, f.filename)}
                              className="text-error hover:text-red-700 shrink-0"
                            >
                              <span className="material-symbols-outlined text-[14px]">
                                delete
                              </span>
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  </details>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="mt-auto border-t border-outline-variant/20 pt-4 px-2 space-y-1">
          <a
            className="flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:bg-surface-container-highest transition-colors font-body-md text-sm"
            href="#"
          >
            <span className="material-symbols-outlined">settings</span>
            Settings
          </a>
          <Link
            to="/help"
            className={`flex items-center gap-3 px-3 py-2 rounded-lg text-on-surface-variant hover:bg-surface-container-highest transition-colors font-body-md text-sm cursor-pointer ${activeTab === 'help' ? 'text-primary font-bold bg-primary-fixed/30' : ''}`}
          >
            <span className="material-symbols-outlined">help</span>
            Support
          </Link>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="ml-64 flex-1 flex flex-col min-h-screen relative z-10">
        {/* Top Nav Bar Shell */}
        <header className="fixed top-0 right-0 left-64 h-16 bg-surface/80 backdrop-blur-md shadow-sm z-10 flex justify-between items-center px-gutter">
          <div className="flex items-center gap-4">
            <nav className="flex text-on-surface-variant font-label-md text-sm">
              <span>
                Workspace (Role:{" "}
                <span className="font-bold text-primary">
                  {role.toUpperCase()}
                </span>
                )
              </span>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <button
              onClick={handleLogout}
              className="bg-error text-white px-4 py-1.5 rounded-lg text-sm font-bold hover:bg-red-700 transition-colors"
            >
              Logout
            </button>
          </div>
        </header>

        {/* Canvas Content */}
        <div className="mt-16 p-stack-lg flex-1">{children}</div>

        {/* Atmospheric Element: Subtle background glow */}
        <div className="fixed bottom-0 right-0 w-[600px] h-[600px] bg-primary/5 blur-[120px] rounded-full pointer-events-none -z-10"></div>
        <div className="fixed top-0 left-64 w-[400px] h-[400px] bg-secondary-container/10 blur-[100px] rounded-full pointer-events-none -z-10"></div>
      </main>
    </div>
  );
};

export default Layout;
