let textPointer = 0;

function typeWriter() {
    return new Promise((resolve, reject) => {
        const speed = 50;
        let textArray = [
            "AI Web3 Series-A funding from California...",
            "Climate change investor for Pre-Seed in Hong Kong...",
            "VC for Seed in Singapore...",
            "Investment funds in Japan...",
            "Cloud Tech Angel Investors...",
            "Venture Capitalists in Central Asia...",
        ];
        let target = document.getElementById("search").placeholder;
        let text = textArray[textPointer];
        if (textPointer === textArray.length - 1) {
            textPointer = 0;
        } else {
            textPointer++;
        }
        for (let i = 0; i < text.length; i++) {
            setTimeout(() => {
                target += text.charAt(i);
                document.getElementById("search").placeholder = target;
                if (i === text.length - 1) {
                    setTimeout(resolve, 1000);
                }
            }, speed * i);
        }
    });
}

function eraseWriter() {
    return new Promise((resolve, reject) => {
        const speed = 30;
        var text = document.getElementById("search").placeholder;
        if (text.length > 0) {
            text = text.slice(0, -1);
            document.getElementById("search").placeholder = text;
            setTimeout(() => {
                eraseWriter().then(resolve);
            }, speed);
        } else {
            resolve();
        }
    });
}

async function startTyping() {
    while (true) {
        await eraseWriter();
        await typeWriter();
    }
}

document.addEventListener("DOMContentLoaded", function () {
    setTimeout(startTyping, 1500);
});
