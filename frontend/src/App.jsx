import { useState, useEffect } from "react";
import "./App.css";
import profilePic from "./assets/profile.png";
import { version } from "../package.json";

// Icons
import { FaGithub, FaLinkedin } from "react-icons/fa";
import { MdEmail, MdDarkMode, MdLightMode } from "react-icons/md";
import { HiDocumentText } from "react-icons/hi";

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
        <p className="subtitle">Cloud & DevOps Engineer</p>

        <section className="about">
          <h2>About Me</h2>
          <p>
            I’m a Cloud & DevOps Engineer based in Indianapolis, working for Eli Lilly. My work spans software engineering, DevOps, cloud infrastructure, operations, and production support. I focus on automation, reliability, and building clean, scalable systems. I’m always open to collaborating on new projects.
          </p>
        </section>

        <div className="links">

          <a href="https://github.com/cullancarey" target="_blank" rel="noopener noreferrer">
            <FaGithub className="icon" />
            GitHub
          </a>

          <a href="https://www.linkedin.com/in/cullancarey" target="_blank" rel="noopener noreferrer">
            <FaLinkedin className="icon" />
            LinkedIn
          </a>

          <a href="/resume.pdf" target="_blank" rel="noopener noreferrer">
            <HiDocumentText className="icon" />
            Resume
          </a>

          <a href="mailto:cullancarey@gmail.com">
            <MdEmail className="icon" />
            Email
          </a>
        </div>
      </main>

      {/* Footer with Version */}
      <footer className="footer">
        <p>v{version}</p>
      </footer>
    </div>
  );
}

export default App;