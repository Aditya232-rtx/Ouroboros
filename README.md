# Ouroboros Landing Page

A modern, secure landing page for Ouroboros - an autonomous AI security platform for GitHub repositories.

## Features

- 🎨 **Modern Design**: Clean, professional interface matching the Figma design specification
- 🌓 **Dark Mode**: Toggle between light and dark themes with smooth transitions
- 🔒 **Security First**: Comprehensive security headers and input validation
- ⚡ **Performance**: Optimized with Next.js 16 and React 19
- 🎭 **Animations**: Smooth CSS animations including the iconic Ouroboros symbol
- 📱 **Responsive**: Fully responsive design that works on all devices
- ♿ **Accessible**: WCAG compliant with proper focus states and ARIA labels

## Technology Stack

- **Framework**: Next.js 16.1.4
- **UI Library**: React 19.2.3
- **Styling**: Tailwind CSS v4
- **Fonts**: Inter (UI) & JetBrains Mono (code)
- **Language**: TypeScript

## Design Elements

### Color Palette
- **Primary**: Emerald (#10b981) - Security/Success
- **Secondary**: Blue (#3b82f6) - Technical/Trust
- **Background Light**: #f8fafc
- **Background Dark**: #0f172a

### Interactive Elements
- **Interactive Grid Background**: Canvas-based grid with mouse tracking and glow effects
  - Mouse tracking with emerald glow trail
  - Idle animation with random cell movements
  - Smooth fade effect for visual depth
- Animated rotating Ouroboros symbol with pulsing animation
- Smooth gradient orbs with pulse effects
- Floating status labels ("fixing...", "validating")
- Hover effects and smooth transitions throughout

## Security Features

The application implements multiple security best practices:

1. **HTTP Security Headers**:
   - Strict-Transport-Security (HSTS)
   - X-Frame-Options (Clickjacking protection)
   - X-Content-Type-Options (MIME sniffing protection)
   - X-XSS-Protection
   - Referrer-Policy
   - Permissions-Policy

2. **Input Validation**:
   - GitHub URL pattern validation
   - XSS prevention through React's built-in protection
   - Safe event handlers

3. **Accessibility**:
   - Keyboard navigation support
   - ARIA labels for screen readers
   - Focus visible states

## Getting Started

### Prerequisites
- Node.js 20+ 
- npm or yarn

### Installation

1. Clone the repository:
\`\`\`bash
git clone <repository-url>
cd ouroboros-v1
\`\`\`

2. Install dependencies:
\`\`\`bash
npm install
\`\`\`

3. Run the development server:
\`\`\`bash
npm run dev
\`\`\`

4. Open [http://localhost:3000](http://localhost:3000) in your browser

### Build for Production

\`\`\`bash
npm run build
npm start
\`\`\`

## Project Structure

\`\`\`
ouroboros-v1/
├── app/
│   ├── globals.css       # Global styles and animations
│   ├── layout.tsx        # Root layout with fonts
│   └── page.tsx          # Main landing page
├── public/               # Static assets
├── next.config.ts        # Next.js config with security headers
└── package.json          # Dependencies
\`\`\`

## Custom Animations

The page includes several custom CSS animations:

- **slither**: Animates the Ouroboros path drawing
- **spin-slow**: Slow rotation for outer circle (10s)
- **spin-reverse**: Counter rotation for inner circle (15s)
- **pulse-slow**: Gentle pulsing for gradient orbs
- **bounce-slow**: Floating effect for status labels

## Customization

### Colors
Edit the color variables in `app/globals.css`:
\`\`\`css
:root {
  --background: #f8fafc;
  --foreground: #0f172a;
}
\`\`\`

### Fonts
Change fonts in `app/layout.tsx` by importing different Google Fonts.

### Content
Update text and links in `app/page.tsx`.

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Performance

- Lighthouse Score: 95+
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s

## License

MIT License - feel free to use this for your projects!

## Author

Created for Ouroboros AI - Autonomous Repository Security

---

Built with ❤️ using Next.js and Tailwind CSS
