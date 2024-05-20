const menus = [
    // { menu: "user-menu", button: "user-menu-button" },
    { menu: "industry-options-menu", button: "industry-options" },
    { menu: "sorting-options-menu", button: "sorting-options" },
    { menu: "round-options-menu", button: "round-options" },
    { menu: "country-options-menu", button: "country-options" },
];

const showClasses = ["transform", "opacity-100", "scale-100"];
const hideClasses = ["opacity-0", "scale-95", "pointer-events-none"];

menus.forEach(({ menu, button }) => {
    const menuElement = document.getElementById(menu);
    const buttonElement = document.getElementById(button);

    document.addEventListener("click", (event) => {
        if (!menuElement.contains(event.target) && !buttonElement.contains(event.target)) {
            menuElement.classList.remove(...showClasses);
            menuElement.classList.add(...hideClasses);
        }
    });

    buttonElement.onclick = () => {
        if (menuElement.classList.contains(hideClasses[0])) {
            menuElement.classList.add(...showClasses);
            menuElement.classList.remove(...hideClasses);
        } else {
            menuElement.classList.remove(...showClasses);
            menuElement.classList.add(...hideClasses);
        }
    };
});
