/** @type {import('tailwindcss').Config} */
module.exports = {
    mode: "jit",
    content: ["./src/project/templates/**/*.{html,htm}"],
    theme: {
        extend: {
            gridTemplateColumns: {
                "auto-repeat": "repeat(auto-fit, 12rem)",
                "auto-repeat-mobile": "repeat(auto-fit, 9rem)",
            },
        },
    },
    darkMode: "class",
    plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
};
