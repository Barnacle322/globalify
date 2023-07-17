/** @type {import('tailwindcss').Config} */
module.exports = {
  mode: 'jit',
  content: ["./server/src/project/templates/**/*.{html,htm}"],
  theme: {
    extend: {
      gridTemplateColumns: {
        'auto-repeat': 'repeat(auto-fit, 12rem)',
        'auto-repeat-mobile': 'repeat(auto-fit, 9rem)',
      },
      keyframes: {
        wiggle: {
          '0%, 100%': { transform: 'rotate(-1deg)' },
          '50%': { transform: 'rotate(1deg)' },
        },
        flyoff: {
          '0%': {transform: 'translateX(0) translateY(0)'},
          '25%': {transform: 'translateX(0) translateY(0)'},
          '100%': {transform: 'translateX(1500px) translateY(-1500px)'}
        },
        fadeoff: {
          '0%, 25%': {opacity: '0'},
          '100%': {opacity: '1'},
        }
      }, 
      animation: {
        wiggle: 'wiggle 0.2s ease-in-out infinite',
        flyoff: 'flyoff 3s ease-in forwards',
        fadeoff: 'fadeoff 1s ease-in-out forwards'
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/line-clamp'),
  ],
}
