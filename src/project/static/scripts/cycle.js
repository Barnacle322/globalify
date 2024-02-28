let theListElement = document.getElementById("thelist");
let theListChildren = theListElement.children;

function cycleForward() {
    theListChildren[0].classList.add("fade-out");
    theListChildren[1].classList.add("slide-left");
    theListChildren[2].classList.add("slide-left");
    // Remove the first element from the DOM after the animation is done and put it at the end
    setTimeout(() => {
        theListChildren[0].classList.remove("fade-out");
        theListChildren[1].classList.remove("slide-left");
        theListChildren[2].classList.remove("slide-left");
        theListElement.appendChild(theListChildren[0]);
        theListChildren[2].classList.add("short-fade-in");
        setTimeout(() => {
            theListChildren[2].classList.remove("short-fade-in");
        }, 300);
    }, 300);
}

function cycleBack() {
    theListChildren[2].classList.add("fade-out");
    theListChildren[1].classList.add("slide-right");
    theListChildren[0].classList.add("slide-right");
    // Remove the last element from the DOM after the animation is done and put it at the beginning
    setTimeout(() => {
        theListChildren[2].classList.remove("fade-out");
        theListChildren[1].classList.remove("slide-right");
        theListChildren[0].classList.remove("slide-right");
        theListElement.insertBefore(theListChildren[2], theListChildren[0]);
        theListChildren[0].classList.add("short-fade-in");
        setTimeout(() => {
            theListChildren[0].classList.remove("short-fade-in");
        }, 300);
    }, 300);
}
