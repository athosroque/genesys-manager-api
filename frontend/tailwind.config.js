/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#FF4F1F', hover: '#E8461A', soft: '#FFF1EB' },
        ink: '#1A1A1A',
        canvas: '#F4F6F8',
        peach: '#FFF5F0',
        sidebar: '#EBF5FF',
        ice: { DEFAULT: '#E6F4F9' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 8px 30px rgba(26, 26, 26, 0.06)',
      },
    },
  },
  plugins: [],
}
