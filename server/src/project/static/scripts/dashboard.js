let user_menu = document.getElementById("user-menu");
let user_menu_button = document.getElementById("user-menu-button");

user_menu_button.onclick = () => {
    if (user_menu.classList.contains("opacity-0")) {
        user_menu.classList.add("transform", "opacity-100", "scale-100");
        user_menu.classList.remove("opacity-0", "scale-95", "pointer-events-none");
    } else {
        user_menu.classList.remove("transform", "opacity-100", "scale-100");
        user_menu.classList.add("opacity-0", "scale-95", "pointer-events-none");
    }
};
