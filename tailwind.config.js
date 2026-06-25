/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./src/project/templates/**/*.{html,htm}",
        "./src/project/static/scripts/**/*.js",
    ],
    theme: {
        extend: {
            colors: {
                brand: { DEFAULT: "#0C72D3", deep: "#0B5BA8", tint: "#E6F0FB" },
                green: { DEFAULT: "#0E7A4F", tint: "#E7F2EB" },
                paper: "#FBFAF6", panel: "#F5F2E9", surface: "#FFFFFF",
                ink: "#15120B", soft: "#544D3C", faint: "#8A8470",
                rule: "#E6E0D2", "rule-2": "#EDE8DC",
            },
            fontFamily: {
                display: ['"Fraunces"', "serif"],
                poppins: ['"Poppins"', "sans-serif"],
                mono: ['"Space Mono"', "ui-monospace", "monospace"],
            },
            typography: {
                // Ledger prose theme — used by legal pages (privacy/terms/refund)
                DEFAULT: {
                    css: {
                        "--tw-prose-body": "#544D3C", // soft
                        "--tw-prose-headings": "#15120B", // ink
                        "--tw-prose-links": "#0C72D3", // brand
                        "--tw-prose-bold": "#15120B", // ink
                        "--tw-prose-counters": "#8A8470", // faint
                        "--tw-prose-bullets": "#E6E0D2", // rule
                        "--tw-prose-hr": "#E6E0D2", // rule
                        "--tw-prose-quotes": "#15120B",
                        "--tw-prose-quote-borders": "#E6E0D2",
                        "--tw-prose-captions": "#8A8470",
                        "--tw-prose-th-borders": "#E6E0D2",
                        "--tw-prose-td-borders": "#EDE8DC",
                        maxWidth: "68ch",
                        h1: { fontFamily: '"Fraunces", serif', fontWeight: "600", letterSpacing: "-0.02em" },
                        h2: { fontFamily: '"Fraunces", serif', fontWeight: "600", letterSpacing: "-0.01em" },
                        h3: { fontFamily: '"Fraunces", serif', fontWeight: "600" },
                        a: { textDecoration: "none", fontWeight: "500" },
                        "a:hover": { textDecoration: "underline" },
                    },
                },
            },
            maxWidth: {
                "8xl": "90rem",
            },
            animation: {
                border: "border 4s ease infinite",
                "slide-in-right": "slide-in-right 0.4s ease",
                "slide-out-right": "slide-out-right 0.4s ease",
                "slide-in-left": "slide-in-left 0.3s",
                "slide-out-left": "slide-out-left 0.3s",
                "fade-in": "fade-in 0.5s ease",
                "fade-out": "fade-out 0.5s ease",
                "zoom-in": "zoom-in 0.1s ease",
                "zoom-out": "zoom-out 0.1s ease",
                "disappear-instantly": "disappear-instantly 0.1s ease-in-out",
                breathe: "breathe 1.5s ease infinite",
            },
            keyframes: {
                border: {
                    "0%, 100%": { backgroundPosition: "0% 50%" },
                    "50%": { backgroundPosition: "100% 50%" },
                },
                "slide-in-right": {
                    "0%": { transform: "translateX(100%)" },
                    "100%": { transform: "translateX(0)" },
                },
                "slide-out-right": {
                    "0%": { transform: "translateX(0)" },
                    "100%": { transform: "translateX(100%)" },
                },
                "slide-in-left": {
                    "0%": { transform: "translateX(-100%)" },
                    "100%": { transform: "translateX(0)" },
                },
                "slide-out-left": {
                    "0%": { transform: "translateX(0)" },
                    "100%": { transform: "translateX(-100%)" },
                },
                "fade-in": {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" },
                },
                "fade-out": {
                    "0%": { opacity: "1" },
                    "100%": { opacity: "0" },
                },
                "zoom-in": {
                    "0%": { transform: "scale(0.95)", opacity: "0" },
                    "100%": { transform: "scale(1)", opacity: "1" },
                },
                "zoom-out": {
                    "0%": { transform: "scale(1)", opacity: "1" },
                    "100%": { transform: "scale(0.95)", opacity: "0" },
                },
                "disappear-instantly": {
                    "0%": { opacity: "1" },
                    "100%": { opacity: "0" },
                },
                breathe: {
                    "0%, 100%": { transform: "scale(1)", opacity: "0.4" },
                    "50%": { transform: "scale(1.10)", opacity: "1" },
                },
            },
        },
    },
    plugins: [
        require("@tailwindcss/forms"),
        require("@tailwindcss/typography"),
        require("@tailwindcss/container-queries"),
    ],
};
