import React, { useState, useEffect } from "react";
import Layout from "./Layout";

function Admin() {
  const [departments, setDepartments] = useState({});
  const [users, setUsers] = useState({});
  const username = localStorage.getItem("username");

  // Form states
  const [newDept, setNewDept] = useState("");
  const [newUser, setNewUser] = useState({
    username: "",
    password: "",
    role: "employee",
    access: "",
  });
  const [accessEdits, setAccessEdits] = useState({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const authHeader = {
        "x-username": username,
        "Cache-Control": "no-cache",
      };

      const deptRes = await fetch(
        `http://127.0.0.1:8000/admin/departments?t=${Date.now()}`,
        { headers: authHeader },
      );
      const deptData = await deptRes.json();
      setDepartments(deptData);

      const userRes = await fetch(
        `http://127.0.0.1:8000/admin/users?t=${Date.now()}`,
        { headers: authHeader },
      );
      const userData = await userRes.json();
      setUsers(userData);

      const initialAccess = {};
      Object.keys(userData).forEach((u) => {
        initialAccess[u] = (userData[u].allowed_departments || []).join(",");
      });
      setAccessEdits(initialAccess);
    } catch (e) {
      console.error(e);
    }
  };

  const addDepartment = async () => {
    const name = newDept.trim().toLowerCase();
    if (!name) return;
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/admin/departments/${name}`,
        {
          method: "POST",
          headers: { "x-username": username },
        },
      );
      const data = await res.json();
      if (data.status === "success") {
        setNewDept("");
        loadData();
      } else {
        alert(
          "Failed to create department: " + (data.detail || "Unknown error"),
        );
      }
    } catch (e) {
      alert("Error adding department.");
    }
  };

  const toggleDeptSuspend = async (name) => {
    await fetch(`http://127.0.0.1:8000/admin/departments/${name}/suspend`, {
      method: "PUT",
      headers: { "x-username": username },
    });
    loadData();
  };

  const deleteDepartment = async (name) => {
    if (!window.confirm(`Delete department ${name}? This will clear all its data.`)) return;
    await fetch(`http://127.0.0.1:8000/admin/departments/${name}`, {
      method: "DELETE",
      headers: { "x-username": username },
    });
    loadData();
  };

  const addUser = async () => {
    const { username: u, password: p, role: r, access: a } = newUser;
    const cleanUser = u.trim().toLowerCase();
    const cleanPass = p.trim();
    if (!cleanUser || !cleanPass) {
      alert("Username and password required");
      return;
    }

    const allowed = a.trim()
      ? a
          .split(",")
          .map((s) => s.trim())
          .filter((s) => s)
      : [];

    try {
      const res = await fetch(`http://127.0.0.1:8000/admin/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-username": username },
        body: JSON.stringify({
          username: cleanUser,
          password: cleanPass,
          role: r,
          allowed_departments: allowed,
        }),
      });
      const data = await res.json();
      if (data.status === "success") {
        setNewUser({
          username: "",
          password: "",
          role: "employee",
          access: "",
        });
        loadData();
      } else {
        alert("Failed to create user: " + (data.detail || "Unknown error"));
      }
    } catch (e) {
      alert("Error adding user.");
    }
  };

  const toggleUserSuspend = async (name) => {
    await fetch(`http://127.0.0.1:8000/admin/users/${name}/suspend`, {
      method: "PUT",
      headers: { "x-username": username },
    });
    loadData();
  };

  const deleteUser = async (name) => {
    if (!window.confirm(`Delete user ${name}?`)) return;
    await fetch(`http://127.0.0.1:8000/admin/users/${name}`, {
      method: "DELETE",
      headers: { "x-username": username },
    });
    loadData();
  };

  const updateAccess = async (name) => {
    const val = accessEdits[name] || "";
    const depts = val
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s);
    await fetch(`http://127.0.0.1:8000/admin/users/${name}/access`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "x-username": username },
      body: JSON.stringify({ allowed_departments: depts }),
    });
    loadData();
  };

  return (
    <Layout activeTab="admin">
      <div className="max-w-screen-2xl mx-auto h-[calc(100vh-140px)]">
        {/* Dashboard Container */}
        <div className="w-full bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-y-auto h-full">
          {/* Header */}
          <div className="p-6 border-b border-outline-variant/20 flex items-center gap-3">
            <span className="material-symbols-outlined text-primary text-3xl">
              settings_applications
            </span>
            <h1 className="text-headline-md font-headline-md text-on-surface">
              Admin Dashboard
            </h1>
          </div>

          {/* Section: Departments */}
          <div className="p-6 space-y-6">
            <div>
              <h2 className="font-headline-md text-lg mb-4 text-on-surface">
                Departments
              </h2>
              <div className="flex gap-3 items-center">
                <input
                  value={newDept}
                  onChange={(e) => setNewDept(e.target.value)}
                  className="flex-1 border border-outline-variant/40 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none bg-surface-container-low"
                  placeholder="New department name (e.g. sales)"
                  type="text"
                />
                <button
                  onClick={addDepartment}
                  className="bg-success text-white px-6 py-2 rounded-lg text-sm font-bold hover:opacity-90 transition-opacity flex items-center gap-2 shrink-0"
                >
                  <span className="material-symbols-outlined text-lg">
                    add_circle
                  </span>
                  Create Department
                </button>
              </div>
            </div>

            {/* Departments Table */}
            <div className="overflow-x-auto rounded-lg border border-outline-variant/20">
              <table className="w-full text-left border-collapse">
                <thead className="bg-surface-container-low font-label-md text-on-surface-variant uppercase text-xs tracking-wider">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Department</th>
                    <th className="px-6 py-3 font-semibold">Status</th>
                    <th className="px-6 py-3 font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10 text-sm font-body-md">
                  {Object.entries(departments).map(([d, info]) => {
                    const isActive = info.status === "active";
                    return (
                      <tr
                        key={d}
                        className="hover:bg-surface-container-low/30 transition-colors"
                      >
                        <td className="px-6 py-4 font-medium uppercase">{d}</td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-bold ${isActive ? "bg-success-container text-on-success-container" : "bg-warning-container text-on-warning-container"}`}
                          >
                            {info.status}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex gap-2">
                            <button
                              onClick={() => toggleDeptSuspend(d)}
                              className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${isActive ? "bg-warning text-black/80 hover:bg-warning-container" : "bg-success text-white hover:opacity-90"}`}
                            >
                              {isActive ? "Suspend" : "Activate"}
                            </button>
                            <button
                              onClick={() => deleteDepartment(d)}
                              className="bg-error text-white px-3 py-1.5 rounded text-xs font-bold hover:bg-red-700 transition-colors"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section: Users */}
          <div className="p-6 pt-0 space-y-6">
            <div>
              <h2 className="font-headline-md text-lg mb-4 text-on-surface">
                Users
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                <input
                  value={newUser.username}
                  onChange={(e) =>
                    setNewUser({ ...newUser, username: e.target.value })
                  }
                  className="border border-outline-variant/40 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none bg-surface-container-low"
                  placeholder="Username"
                  type="text"
                />
                <input
                  value={newUser.password}
                  onChange={(e) =>
                    setNewUser({ ...newUser, password: e.target.value })
                  }
                  className="border border-outline-variant/40 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none bg-surface-container-low"
                  placeholder="Password"
                  type="password"
                />
                <select
                  value={newUser.role}
                  onChange={(e) =>
                    setNewUser({ ...newUser, role: e.target.value })
                  }
                  className="border border-outline-variant/40 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none bg-surface-container-low"
                >
                  <option value="employee">Employee</option>
                  <option value="manager">Manager</option>
                  <option value="admin">Admin</option>
                </select>
                <input
                  value={newUser.access}
                  onChange={(e) =>
                    setNewUser({ ...newUser, access: e.target.value })
                  }
                  className="border border-outline-variant/40 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none bg-surface-container-low"
                  placeholder="Access depts (e.g. hr,it)"
                  type="text"
                />
                <button
                  onClick={addUser}
                  className="bg-success text-white px-6 py-2 rounded-lg text-sm font-bold hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                >
                  <span className="material-symbols-outlined text-lg">
                    person_add
                  </span>
                  Create User
                </button>
              </div>
            </div>

            {/* Users Table */}
            <div className="overflow-x-auto rounded-lg border border-outline-variant/20">
              <table className="w-full text-left border-collapse">
                <thead className="bg-surface-container-low font-label-md text-on-surface-variant uppercase text-xs tracking-wider">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Username</th>
                    <th className="px-6 py-3 font-semibold">Role</th>
                    <th className="px-6 py-3 font-semibold">Access</th>
                    <th className="px-6 py-3 font-semibold">Status</th>
                    <th className="px-6 py-3 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/10 text-sm font-body-md">
                  {Object.entries(users).map(([u, info]) => {
                    const isActive = (info.status || "active") === "active";
                    return (
                      <tr
                        key={u}
                        className="hover:bg-surface-container-low/30 transition-colors"
                      >
                        <td className="px-6 py-4 font-bold">{u}</td>
                        <td className="px-6 py-4">{info.role}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2">
                            <input
                              value={
                                accessEdits[u] !== undefined
                                  ? accessEdits[u]
                                  : ""
                              }
                              onChange={(e) =>
                                setAccessEdits({
                                  ...accessEdits,
                                  [u]: e.target.value,
                                })
                              }
                              className="bg-white border border-outline-variant/30 rounded px-2 py-1 text-xs w-32 focus:outline-none focus:ring-1 focus:ring-primary"
                              type="text"
                            />
                            <button
                              onClick={() => updateAccess(u)}
                              className="bg-primary text-white p-1.5 rounded hover:bg-primary-container transition-colors"
                            >
                              <span className="material-symbols-outlined text-[14px]">
                                save
                              </span>
                            </button>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span
                            className={`px-3 py-1 rounded-full text-xs font-bold ${isActive ? "bg-success-container text-on-success-container" : "bg-warning-container text-on-warning-container"}`}
                          >
                            {info.status || "active"}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex gap-2">
                            <button
                              onClick={() => toggleUserSuspend(u)}
                              className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${isActive ? "bg-warning text-black/80 hover:bg-warning-container" : "bg-success text-white hover:opacity-90"}`}
                            >
                              {isActive ? "Suspend" : "Activate"}
                            </button>
                            <button
                              onClick={() => deleteUser(u)}
                              className="bg-error text-white px-3 py-1.5 rounded text-xs font-bold hover:bg-red-700 transition-colors"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default Admin;
