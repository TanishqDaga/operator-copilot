/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0A0C0F',
        panel: '#111418',
        panel2: '#161A20',
        raised: '#1B2027',
        line: '#232830',
        line2: '#2E3540',
        ink: '#E8EBEF',
        ink2: '#A3ACB9',
        ink3: '#6B7482',
        cat: { DEFAULT: '#FFCD11', dim: '#C9A10A', ink: '#1A1400' },
        safe: { DEFAULT: '#2FD07F', bg: '#0C2419' },
        warn: { DEFAULT: '#FF8A1F', bg: '#2A1806' },
        crit: { DEFAULT: '#FF4D4F', bg: '#2E0B0C' },
        info: { DEFAULT: '#5AA9FF', bg: '#0B1B2E' },
        anom: { DEFAULT: '#B38CFF', bg: '#1C1330' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Segoe UI', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'Consolas', 'monospace'],
      },
      fontSize: {
        '2xs': ['11px', '14px'],
      },
      boxShadow: {
        card: '0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.6)',
      },
      keyframes: {
        pulseRing: { '0%': { boxShadow: '0 0 0 0 rgba(255,77,79,0.55)' }, '100%': { boxShadow: '0 0 0 18px rgba(255,77,79,0)' } },
        fadeUp: { '0%': { opacity: 0, transform: 'translateY(6px)' }, '100%': { opacity: 1, transform: 'none' } },
        rise: { '0%': { transform: 'translateY(8px) scale(0.98)' }, '100%': { transform: 'none' } },
        slideIn: { '0%': { opacity: 0, transform: 'translateX(24px)' }, '100%': { opacity: 1, transform: 'none' } },
        flash: { '0%': { backgroundColor: 'rgba(255,205,17,0.18)' }, '100%': { backgroundColor: 'transparent' } },
        critGlow: { '0%,100%': { opacity: 0.55 }, '50%': { opacity: 1 } },
      },
      animation: {
        pulseRing: 'pulseRing 1.2s ease-out infinite',
        fadeUp: 'fadeUp .35s cubic-bezier(.2,.7,.2,1) both',
        rise: 'rise .35s cubic-bezier(.2,.7,.2,1)',
        slideIn: 'slideIn .3s cubic-bezier(.2,.7,.2,1) both',
        flash: 'flash 1.2s ease-out',
        critGlow: 'critGlow 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
