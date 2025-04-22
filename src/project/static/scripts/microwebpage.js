const theListElement = document.getElementById("gallery");

function cycleForward() {
    const items = theListElement.children;
    if (!items.length) return;

    // Animate the first slide out
    items[0].classList.add("fade-scale-out");

    // Animate others sliding left
    for (let i = 1; i < items.length; i++) {
        items[i].classList.add("slide-left");
    }

    // After animation ends, move first to the end
    setTimeout(() => {
        items[0].classList.remove("fade-scale-out");
        for (let i = 1; i < items.length; i++) {
            items[i].classList.remove("slide-left");
        }

        theListElement.appendChild(items[0]);

        let last = theListElement.children[theListElement.children.length - 1];
        last.classList.add("short-fade-in");
        setTimeout(() => {
            last.classList.remove("short-fade-in");
        }, 300);
    }, 300);
}

function cycleBack() {
    const items = theListElement.children;
    if (!items.length) return;

    let last = items[items.length - 1];
    last.classList.add("fade-scale-out");

    for (let i = 0; i < items.length; i++) {
        items[i].classList.add("slide-right");
    }

    setTimeout(() => {
        last.classList.remove("fade-scale-out");
        for (let i = 0; i < items.length; i++) {
            items[i].classList.remove("slide-right");
        }

        theListElement.insertBefore(last, items[0]);
        items[0].classList.add("short-fade-in");
        setTimeout(() => {
            items[0].classList.remove("short-fade-in");
        }, 300);
    }, 300);
}
