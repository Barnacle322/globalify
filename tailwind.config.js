/** @type {import('tailwindcss').Config} */
module.exports = {
    mode: "jit",
    content: ["./src/project/templates/**/*.{html,htm}"],
    theme: {
        extend: {
            animation: {
                border: "border 4s ease infinite",
            },
            keyframes: {
                border: {
                    "0%, 100%": { backgroundPosition: "0% 50%" },
                    "50%": { backgroundPosition: "100% 50%" },
                },
            },
        },
    },
    darkMode: "class",
    plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
};
