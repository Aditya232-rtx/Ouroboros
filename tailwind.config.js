/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: 'class',
    content: [
        './app/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                primary: '#10b981', // Emerald green for security/success feel
                secondary: '#3b82f6', // Blue for technical/trust
                'background-light': '#f8fafc',
                'background-dark': '#0f172a',
                'surface-light': '#ffffff',
                'surface-dark': '#1e293b',
                'border-light': '#e2e8f0',
                'border-dark': '#334155',
            },
            fontFamily: {
                sans: ['var(--font-inter)', 'Inter', 'sans-serif'],
                mono: ['var(--font-jetbrains-mono)', 'JetBrains Mono', 'monospace'],
            },
            borderRadius: {
                DEFAULT: '0.5rem',
            },
            boxShadow: {
                glow: '0 0 20px rgba(16, 185, 129, 0.15)',
            },
        },
    },
    plugins: [],
};
