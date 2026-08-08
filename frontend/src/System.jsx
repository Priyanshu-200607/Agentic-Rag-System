import React from "react";
import Layout from "./Layout";
import SystemStatus from "./SystemStatus";
import LogViewer from "./LogViewer";

function System() {
  const role = localStorage.getItem("role");

  if (role !== "admin") {
    return (
      <Layout activeTab="system">
        <div className="p-10 text-center text-error font-bold">Unauthorized</div>
      </Layout>
    );
  }

  return (
    <Layout activeTab="system">
      <div className="max-w-screen-2xl mx-auto flex flex-col gap-6 h-[calc(100vh-140px)]">
        {/* System Status Container (Top Row) */}
        <div className="shrink-0">
          <SystemStatus />
        </div>

        {/* System Container (Bottom for logs) */}
        <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden flex-1 flex flex-col">
          <LogViewer />
        </div>
      </div>
    </Layout>
  );
}

export default System;
