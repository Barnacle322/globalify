/** @type {import('tailwindcss').Config} */
module.exports = {
    mode: "jit",
    content: ["./src/project/templates/**/*.{html,htm}"],
    // theme: {
    //     extend: {
    //         colors: {
    //             "deep-purple": "#231645",
    //         },
    //         maxWidth: {
    //             "8xl": "90rem",
    //         },
    //         animation: {
    //             border: "border 4s ease infinite",
    //             "slide-in-right": "slide-in-right 0.4s ease",
    //             "slide-out-right": "slide-out-right 0.4s ease",
    //             "slide-in-left": "slide-in-left 0.3s",
    //             "slide-out-left": "slide-out-left 0.3s",
    //             "fade-in": "fade-in 0.5s ease",
    //             "fade-out": "fade-out 0.5s ease",
    //             "zoom-in": "zoom-in 0.1s ease",
    //             "zoom-out": "zoom-out 0.1s ease",
    //             "disappear-instantly": "disappear-instantly 0.1s ease-in-out",
    //             breathe: "breathe 1.5s ease infinite",
    //         },
    //         keyframes: {
    //             border: {
    //                 "0%, 100%": { backgroundPosition: "0% 50%" },
    //                 "50%": { backgroundPosition: "100% 50%" },
    //             },
    //             "slide-in-right": {
    //                 "0%": { transform: "translateX(100%)" },
    //                 "100%": { transform: "translateX(0)" },
    //             },
    //             "slide-out-right": {
    //                 "0%": { transform: "translateX(0)" },
    //                 "100%": { transform: "translateX(100%)" },
    //             },
    //             "slide-in-left": {
    //                 "0%": { transform: "translateX(-100%)" },
    //                 "100%": { transform: "translateX(0)" },
    //             },
    //             "slide-out-left": {
    //                 "0%": { transform: "translateX(0)" },
    //                 "100%": { transform: "translateX(-100%)" },
    //             },
    //             "fade-in": {
    //                 "0%": { opacity: "0" },
    //                 "100%": { opacity: "1" },
    //             },
    //             "fade-out": {
    //                 "0%": { opacity: "1" },
    //                 "100%": { opacity: "0" },
    //             },
    //             "zoom-in": {
    //                 "0%": { transform: "scale(0.95)", opacity: "0" },
    //                 "100%": { transform: "scale(1)", opacity: "1" },
    //             },
    //             "zoom-out": {
    //                 "0%": { transform: "scale(1)", opacity: "1" },
    //                 "100%": { transform: "scale(0.95)", opacity: "0" },
    //             },
    //             "disappear-instantly": {
    //                 "0%": { opacity: "1" },
    //                 "100%": { opacity: "0" },
    //             },
    //             breathe: {
    //                 "0%, 100%": { transform: "scale(1)", opacity: "0.4" },
    //                 "50%": { transform: "scale(1.10)", opacity: "1" },
    //             },
    //         },
    //     },
    // },
    plugins: [
        require("@tailwindcss/forms"),
        require("@tailwindcss/typography"),
    ],
};
