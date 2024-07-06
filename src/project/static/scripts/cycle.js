let theListElement = document.getElementById("thelist");
let theListChildren = theListElement.children;

function cycleForward() {
    theListChildren[0].classList.add("fade-scale-out");
    for (let i = 1; i < theListChildren.length; i++) {
        theListChildren[i].classList.add("slide-left");
    }
    setTimeout(() => {
        theListChildren[0].classList.remove("fade-scale-out");
        for (let i = 1; i < theListChildren.length; i++) {
            theListChildren[i].classList.remove("slide-left");
        }
        theListElement.appendChild(theListChildren[0]);
        let lastChild = theListChildren[theListChildren.length - 1];
        lastChild.classList.add("short-fade-in");
        setTimeout(() => {
            lastChild.classList.remove("short-fade-in");
        }, 300);
    }, 300);
}

function cycleBack() {
    let lastChild = theListChildren[theListChildren.length - 1];
    lastChild.classList.add("fade-scale-out");
    theListChildren[1].classList.add("slide-right");
    theListChildren[0].classList.add("slide-right");

    for (let i = 0; i < theListChildren.length; i++) {
        theListChildren[i].classList.add("slide-right");
    }

    // Remove the last element from the DOM after the animation is done and put it at the beginning
    setTimeout(() => {
        let lastChild = theListChildren[theListChildren.length - 1];
        lastChild.classList.remove("fade-scale-out");
        for (let i = 0; i < theListChildren.length; i++) {
            theListChildren[i].classList.remove("slide-right");
        }
        theListElement.insertBefore(lastChild, theListChildren[0]);
        theListChildren[0].classList.add("short-fade-in");
        setTimeout(() => {
            theListChildren[0].classList.remove("short-fade-in");
        }, 300);
    }, 300);
}
