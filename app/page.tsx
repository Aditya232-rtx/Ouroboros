'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import InteractiveGridBackground from './components/InteractiveGridBackground';

export default function Home() {
  const [isDark, setIsDark] = useState(false);
  const [repoLink, setRepoLink] = useState('');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Check localStorage first, then system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    } else {
      setIsDark(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = !isDark;
    setIsDark(newTheme);

    if (newTheme) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  };

  const handleScan = () => {
    // Validate GitHub URL
    const githubPattern = /^(https?:\/\/)?(www\.)?github\.com\/[\w-]+\/[\w.-]+\/?$/;
    if (repoLink && githubPattern.test(repoLink)) {
      console.log('Scanning repository:', repoLink);
      // Add your scan logic here
    } else {
      alert('Please enter a valid GitHub repository URL');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleScan();
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-slate-50 via-slate-50 to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 transition-colors duration-300">
      {/* Navigation */}
      <nav className="w-full border-b border-slate-200/80 dark:border-slate-800/80 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <svg
                className="w-8 h-8 text-emerald-500"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"
                  fill="currentColor"
                />
                <path
                  d="M12 6c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm0 10c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4z"
                  fill="currentColor"
                />
              </svg>
              <span className="font-semibold text-xl tracking-tight text-slate-900 dark:text-white">
                Ouroboros
              </span>
            </div>

            {/* Navigation Links */}
            <div className="flex items-center space-x-6">
              <button
                onClick={toggleTheme}
                className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
                aria-label="Toggle theme"
              >
                {isDark ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                )}
              </button>
              <Link
                href="#"
                className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-emerald-500 dark:hover:text-emerald-400 transition-colors"
              >
                Documentation
              </Link>
              <Link
                href="#"
                className="text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-emerald-500 dark:hover:text-emerald-400 transition-colors"
              >
                Login
              </Link>
              <Link
                href="#"
                className="bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-md hover:shadow-lg hover:shadow-emerald-500/25"
              >
                Sign Up
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-grow relative overflow-hidden">
        <InteractiveGridBackground
          gridSize={45}
          gridColor="#e2e8f0"
          darkGridColor="#334155"
          effectColor="rgba(16, 185, 129, 0.3)"
          darkEffectColor="rgba(16, 185, 129, 0.4)"
          trailLength={6}
          idleSpeed={0.15}
          glow={true}
          glowRadius={25}
          showFade={true}
          fadeIntensity={15}
          idleRandomCount={3}
          className="w-full h-full"
        >
          {/* Gradient Orbs */}
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/20 rounded-full blur-[120px] animate-pulse-slow pointer-events-none"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-[120px] animate-pulse-slow-delayed pointer-events-none"></div>

          <div className="flex items-center justify-center min-h-[calc(100vh-8rem)] py-16 md:py-20">
            <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 w-full relative z-10 mb-12">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
                {/* Left Content */}
                <div className="space-y-8">
                  {/* Status Badge */}
                  <div className="inline-flex items-center px-3 py-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-medium backdrop-blur-sm">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse"></span>
                    System Online V1.0
                  </div>

                  {/* Main Heading */}
                  <div className="space-y-4">
                    <h1 className="text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 dark:text-white leading-tight">
                      Autonomous <br />
                      <span className="text-emerald-500">Repository</span> <br />
                      Security
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400 text-lg leading-relaxed max-w-lg">
                      Ouroboros scans, patches, and validates your GitHub repositories in an infinite loop of security optimization.
                    </p>
                  </div>

                  {/* Input Card */}
                  <div className="bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/50 p-6 rounded-2xl shadow-xl dark:shadow-2xl dark:shadow-black/20 backdrop-blur-sm">
                    <label
                      htmlFor="repo-link"
                      className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3"
                    >
                      Enter your GitHub repo link
                    </label>
                    <div className="relative flex items-center">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                      </div>
                      <input
                        id="repo-link"
                        type="text"
                        value={repoLink}
                        onChange={(e) => setRepoLink(e.target.value)}
                        onKeyPress={handleKeyPress}
                        className="block w-full pl-10 pr-24 py-3 border border-slate-200 dark:border-slate-700 dark:bg-slate-900/50 rounded-lg text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm font-mono transition-all"
                        placeholder="github.com/username/project"
                      />
                      <button
                        onClick={handleScan}
                        className="absolute right-1.5 top-1.5 bottom-1.5 bg-slate-900 dark:bg-emerald-500 text-white hover:bg-slate-800 dark:hover:bg-emerald-600 px-4 rounded-md text-sm font-medium transition-colors flex items-center space-x-1"
                      >
                        <span>Scan</span>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </button>
                    </div>
                    <p className="mt-3 text-xs text-slate-500 dark:text-slate-400 flex items-center">
                      <svg className="w-4 h-4 mr-1.5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Auto-fix pull requests supported
                    </p>
                  </div>
                </div>

                {/* Right Animation */}
                <div className="hidden lg:flex justify-center items-center">
                  <div className="relative w-80 h-80">
                    {/* Rotating Border Circles */}
                    <div className="absolute inset-0 border border-slate-200 dark:border-slate-700 rounded-full animate-spin-slow border-dashed"></div>
                    <div className="absolute inset-8 border border-emerald-500/30 rounded-full animate-spin-reverse"></div>

                    {/* Center Ouroboros SVG */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <svg
                        className="text-emerald-500 drop-shadow-[0_0_15px_rgba(16,185,129,0.5)]"
                        width="180"
                        height="180"
                        viewBox="0 0 100 100"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <circle
                          className="opacity-20"
                          cx="50"
                          cy="50"
                          r="35"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="6"
                          strokeLinecap="round"
                        />
                        <path
                          className="ouroboros-path"
                          d="M 50,15 A 35,35 0 1,1 15,50"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="6"
                          strokeLinecap="round"
                        />
                        <circle cx="50" cy="15" r="3" fill="white" />
                      </svg>
                    </div>

                    {/* Floating Labels */}
                    <div className="absolute -right-4 top-10 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-3 py-2 rounded-lg shadow-lg text-xs font-mono text-emerald-500 opacity-80 animate-bounce-slow">
                      fixing...
                    </div>
                    <div className="absolute -left-4 bottom-20 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-3 py-2 rounded-lg shadow-lg text-xs font-mono text-blue-500 opacity-80 animate-pulse">
                      validating
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </InteractiveGridBackground>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 py-10 bg-white dark:bg-slate-900/50 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center text-sm text-slate-500 dark:text-slate-400">
          <div className="flex items-center space-x-2 mb-4 md:mb-0">
            <span className="font-semibold text-slate-700 dark:text-slate-300">Ouroboros AI</span>
            <span>© 2023</span>
          </div>
          <div className="flex space-x-6 items-center">
            <Link href="#" className="hover:text-emerald-500 dark:hover:text-emerald-400 transition-colors">
              Privacy
            </Link>
            <Link href="#" className="hover:text-emerald-500 dark:hover:text-emerald-400 transition-colors">
              Terms
            </Link>
            <Link href="#" className="hover:text-emerald-500 dark:hover:text-emerald-400 transition-colors">
              Status
            </Link>
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="text-emerald-500">Systems Operational</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
