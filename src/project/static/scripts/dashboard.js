let user_menu = document.getElementById("user-menu");
let user_menu_button = document.getElementById("user-menu-button");

// Add a click event listener to the document object
document.addEventListener("click", (event) => {
    // Check if the clicked element is not inside the user_menu div
    if (!user_menu.contains(event.target) && !user_menu_button.contains(event.target)) {
        // If the clicked element is outside the user_menu div, close the div
        user_menu.classList.remove("transform", "opacity-100", "scale-100");
        user_menu.classList.add("opacity-0", "scale-95", "pointer-events-none");
    }
});

user_menu_button.onclick = () => {
    if (user_menu.classList.contains("opacity-0")) {
        user_menu.classList.add("transform", "opacity-100", "scale-100");
        user_menu.classList.remove("opacity-0", "scale-95", "pointer-events-none");
    } else {
        user_menu.classList.remove("transform", "opacity-100", "scale-100");
        user_menu.classList.add("opacity-0", "scale-95", "pointer-events-none");
    }
};