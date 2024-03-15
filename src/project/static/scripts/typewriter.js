let textPointer = 0;
function typeWriter() {
    const speed = 70;
    let textArray = ["Funders", "Founders", "Partners", "Investors", "Collaborators", "Entrepreneurs"];
    let target = document.getElementById("typewriter").innerHTML;
    let text = textArray[textPointer];
    if (textPointer === textArray.length - 1) {
        textPointer = 0;
    } else {
        textPointer++;
    }
    for (let i = 0; i < text.length; i++) {
        setTimeout(() => {
            target += text.charAt(i);
            document.getElementById("typewriter").innerHTML = target;
        }, speed * i);
    }
}

function eraseWriter() {
    var text = document.getElementById("typewriter").innerHTML;
    const speed = 70;
    if (text.length > 0) {
        text = text.slice(0, -1);
        document.getElementById("typewriter").innerHTML = text;
        setTimeout(eraseWriter, speed);
    }
}

document.addEventListener("DOMContentLoaded", function () {
    setInterval(() => {
        setTimeout(eraseWriter, 1000);
        setTimeout(typeWriter, 2000);
    }, 3500);
});
