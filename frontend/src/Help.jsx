import React from "react";
import Layout from "./Layout";

function Help() {
  const role = localStorage.getItem("role") || "employee";

  return (
    <Layout activeTab="help">
      <div className="max-w-screen-2xl mx-auto h-[calc(100vh-140px)]">
        <div className="bg-surface rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden h-full flex flex-col">
          <div className="p-6 border-b border-outline-variant/20 flex items-center gap-3 bg-surface-container-lowest">
            <span className="material-symbols-outlined text-primary text-3xl">menu_book</span>
            <h1 className="text-headline-md font-bold text-on-surface">Application Guide</h1>
          </div>
          
          <div className="p-6 overflow-y-auto space-y-8 text-on-surface font-body-md flex-1">
            <p className="text-on-surface-variant">Welcome to the MSFC RAG Intelligence Engine. Below is a comprehensive guide to help you navigate and utilize the system effectively based on your assigned role.</p>

            <section className="bg-surface-container-low p-6 rounded-lg border border-outline-variant/20 space-y-4">
              <h2 className="font-bold text-xl text-primary flex items-center gap-2">
                <span className="material-symbols-outlined">chat</span>
                Chat Interface
              </h2>
              <p className="text-on-surface-variant">The Chat tab is where you interact directly with the AI, querying the knowledge base.</p>
              
              <div className="space-y-3 pl-4 border-l-2 border-primary/20">
                <h3 className="font-semibold">Starting a Session</h3>
                <p className="text-on-surface-variant text-sm">Click "New Chat" in the sidebar to start a fresh conversation. Previous sessions are saved and listed below it; simply click on an older session to review your history.</p>
                
                <h3 className="font-semibold mt-4">Asking Questions</h3>
                <p className="text-on-surface-variant text-sm">Type your query into the input box at the bottom. While the AI generates a response, a status indicator will display what the system is currently doing (e.g. querying the knowledge graph or generating text).</p>
                
                <h3 className="font-semibold mt-4">Context Filtering</h3>
                <p className="text-on-surface-variant text-sm">If you need information specific to a certain department, ensure that you include context in your query, and the AI will reference the documents uploaded to those specific departments (provided you have access).</p>
              </div>
            </section>

            {role === "admin" && (
              <>
                <section className="bg-surface-container-low p-6 rounded-lg border border-outline-variant/20 space-y-4">
                  <h2 className="font-bold text-xl text-primary flex items-center gap-2">
                    <span className="material-symbols-outlined">dashboard</span>
                    Admin Dashboard
                  </h2>
                  <p className="text-on-surface-variant">The Admin Dashboard provides complete control over users, departments, and system monitoring.</p>
                  
                  <div className="space-y-4 pl-4 border-l-2 border-primary/20">
                    <div>
                      <h3 className="font-semibold">Managing Departments</h3>
                      <ul className="list-disc pl-5 text-on-surface-variant text-sm space-y-1 mt-2">
                        <li><strong>Create:</strong> Enter a department name (alphanumeric, 2-60 characters) and click "Create Department".</li>
                        <li><strong>Suspend/Activate:</strong> Use the toggle button next to any department to temporarily restrict access to its data without deleting it.</li>
                      </ul>
                    </div>

                    <div>
                      <h3 className="font-semibold">Managing Users</h3>
                      <ul className="list-disc pl-5 text-on-surface-variant text-sm space-y-1 mt-2">
                        <li><strong>Create User:</strong> Fill in the username, password, select a role (Employee, Manager, Admin), and type comma-separated department names for their access.</li>
                        <li><strong>Update Access:</strong> In the user table, edit the text box under "Access" and click the save icon to instantly update what departments they can query.</li>
                        <li><strong>Suspend/Delete:</strong> Suspend a user to temporarily revoke login rights, or Delete them to permanently remove their account.</li>
                      </ul>
                    </div>
                  </div>
                </section>
                
                <section className="bg-surface-container-low p-6 rounded-lg border border-outline-variant/20 space-y-4">
                  <h2 className="font-bold text-xl text-primary flex items-center gap-2">
                    <span className="material-symbols-outlined">cloud_upload</span>
                    Knowledge Base Management (File Uploads)
                  </h2>
                  <p className="text-on-surface-variant">Populate the AI's knowledge base by uploading documents directly into specific departments.</p>
                  
                  <div className="space-y-3 pl-4 border-l-2 border-primary/20">
                    <h3 className="font-semibold">How to Upload</h3>
                    <p className="text-on-surface-variant text-sm">Using the left sidebar, select a target department from the dropdown menu, drag-and-drop or browse for your files, and click "Upload". The system will ingest the files into the Vector DB and Knowledge Graph.</p>
                    
                    <h3 className="font-semibold mt-4">Upload History & Cleanup</h3>
                    <p className="text-on-surface-variant text-sm">Scroll down the sidebar to view the "Upload History" categorized by department. From here, you can click the trash icon next to individual files to delete them from the database, or use the "Clear" button to wipe an entire department's data at once.</p>
                  </div>
                </section>

                <section className="bg-surface-container-low p-6 rounded-lg border border-outline-variant/20 space-y-4">
                  <h2 className="font-bold text-xl text-primary flex items-center gap-2">
                    <span className="material-symbols-outlined">monitoring</span>
                    System Monitoring & Logs
                  </h2>
                  <p className="text-on-surface-variant">Keep an eye on system health directly from the Admin Dashboard.</p>
                  
                  <div className="space-y-3 pl-4 border-l-2 border-primary/20">
                    <h3 className="font-semibold">Real-time System Status</h3>
                    <p className="text-on-surface-variant text-sm">The right-hand panel displays live CPU, RAM, and GPU usage metrics. It also shows active background tasks (like file ingestion progress) and current storage usage for the databases.</p>

                    <h3 className="font-semibold mt-4">LLM Configuration</h3>
                    <p className="text-on-surface-variant text-sm">Under the System Status panel, you can hot-swap the active models used for the Master Agent and Department Agents, and adjust the Temperature slider (lower for precision, higher for creativity).</p>

                    <h3 className="font-semibold mt-4">Unified Log Viewer</h3>
                    <p className="text-on-surface-variant text-sm">Located at the bottom of the Admin Dashboard, this terminal-like window streams live backend logs. Use the tabs (All, Query, Task, System) to filter logs by type for easier debugging.</p>
                  </div>
                </section>
              </>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default Help;
