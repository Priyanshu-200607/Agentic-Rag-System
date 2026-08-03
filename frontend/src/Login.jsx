import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch("http://127.0.0.1:8000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim().toLowerCase(),
          password: password.trim(),
        }),
      });

      const data = await response.json();

      if (data.success) {
        localStorage.setItem("username", data.username);
        localStorage.setItem("role", data.role);
        if (data.role === "admin" || data.role === "manager") {
          navigate("/admin");
        } else {
          navigate("/chat");
        }
      } else {
        alert(data.message || "Login failed! Invalid credentials.");
      }
    } catch (error) {
      alert("Error connecting to server.");
    }
  };

  return (
    <div className="bg-tech-gradient min-h-screen flex items-center justify-center p-4 md:p-8 font-sans antialiased text-on-surface">
      <div className="relative z-10 w-full max-w-md glass-panel rounded-xl p-8 md:p-10 flex flex-col gap-stack-lg">
        {/* Header */}
        <div className="text-center flex flex-col items-center gap-stack-sm">
          <div className="w-12 h-12 bg-primary rounded-lg flex items-center justify-center mb-2 shadow-sm">
            <span
              className="material-symbols-outlined text-on-primary text-2xl"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              dataset
            </span>
          </div>
          <h1 className="font-headline-md text-headline-md text-on-surface">
            RAG
          </h1>
          <p className="font-body-md text-body-md text-secondary">
            Intelligence Engine
          </p>
        </div>

        {/* Form */}
        <form className="flex flex-col gap-stack-md" onSubmit={handleLogin}>
          {/* Email Input */}
          <div className="flex flex-col gap-unit">
            <label
              className="font-label-md text-label-md text-on-surface-variant"
              htmlFor="username"
            >
              User Id
            </label>
            <div className="input-glass rounded-xl flex items-center px-4 py-3 h-14">
              <span className="material-symbols-outlined text-secondary mr-3">
                person
              </span>
              <input
                className="bg-transparent border-none w-full p-0 font-body-md text-body-md text-on-surface placeholder:text-outline-variant focus:ring-0 outline-none"
                id="username"
                placeholder="user name"
                required
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
          </div>

          {/* Password Input */}
          <div className="flex flex-col gap-unit">
            <label
              className="font-label-md text-label-md text-on-surface-variant"
              htmlFor="password"
            >
              Password
            </label>
            <div className="input-glass rounded-xl flex items-center px-4 py-3 h-14">
              <span className="material-symbols-outlined text-secondary mr-3">
                lock
              </span>
              <input
                className="bg-transparent border-none w-full p-0 font-body-md text-body-md text-on-surface placeholder:text-outline-variant focus:ring-0 outline-none"
                id="password"
                placeholder="••••••••"
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <div className="flex justify-end mt-[-8px]">
            <a
              className="font-label-md text-label-md text-primary hover:text-primary-container transition-colors"
              href="#"
            >
              Contact Admin
              <br />
            </a>
          </div>

          {/* Submit Button */}
          <button
            className="mt-4 bg-primary hover:bg-primary-container text-on-primary font-label-md text-label-md h-14 rounded-xl flex items-center justify-center gap-2 transition-colors shadow-sm"
            type="submit"
          >
            Sign In
            <span className="material-symbols-outlined text-sm">
              arrow_forward
            </span>
          </button>
        </form>

        {/* Footer / SSO */}
        <div className="flex flex-col gap-stack-md mt-2">
          <div className="flex items-center gap-4">
            <div className="h-px bg-surface-variant flex-1"></div>
            <span className="font-label-md text-label-md text-secondary">
              Or continue with
            </span>
            <div className="h-px bg-surface-variant flex-1"></div>
          </div>
          <button className="bg-transparent border border-outline-variant hover:bg-surface-container-low text-on-surface font-label-md text-label-md h-12 rounded-xl flex items-center justify-center gap-2 transition-colors">
            <span className="material-symbols-outlined text-secondary">
              business
            </span>
            Enterprise SSO
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
