// src/App.jsx
import { useState, useEffect } from "react";
import "./App.css";
import profilePic from "./assets/profile.jpg";

// Icons
import { FaGithub, FaLinkedin, FaTwitter } from "react-icons/fa";
import { MdEmail, MdDarkMode, MdLightMode } from "react-icons/md";
import { BsGlobe } from "react-icons/bs";

function App() {
  const [theme, setTheme] = useState("dark");

  // Apply theme to body attribute
  useEffect(() => {
    document.body.setAttribute("data-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <div className="app">
      <main className="card">

        {/* Light/Dark Mode Button */}
        <button className="theme-toggle" onClick={toggleTheme}>
          {theme === "dark" ? <MdLightMode /> : <MdDarkMode />}
        </button>

        <img src={profilePic} alt="Cullan Carey" className="profile-pic" />

        <h1 className="title">Cullan Carey</h1>
        <p className="subtitle">Cloud & DevOps Engineer • SRE</p>

        <section className="about">
          <h2>About Me</h2>
          <p>
            I'm a Cloud & DevOps Engineer focused on automation, reliability,
            and building clean technical systems. I work hands-on with AWS,
            Kubernetes, CI/CD pipelines, and backend services — always looking
            for ways to improve speed, security, and developer experience.
          </p>
        </section>

        <div className="links">
          <a href="https://www.cullancarey.com" target="_blank" rel="noopener noreferrer">
            <BsGlobe className="icon" />
            Portfolio
          </a>

          <a href="https://github.com/cullancarey" target="_blank" rel="noopener noreferrer">
            <FaGithub className="icon" />
            GitHub
          </a>

          <a href="https://www.linkedin.com/in/cullancarey" target="_blank" rel="noopener noreferrer">
            <FaLinkedin className="icon" />
            LinkedIn
          </a>

          <a href="https://twitter.com/cullancarey" target="_blank" rel="noopener noreferrer">
            <FaTwitter className="icon" />
            Twitter
          </a>

          <a href="mailto:youremail@example.com">
            <MdEmail className="icon" />
            Email
          </a>
        </div>
      </main>
    </div>
  );
}

export default App;