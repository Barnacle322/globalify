const menus = [
    { menu: "user-menu", button: "user-menu-button" },
    { menu: "industry-options", button: "industry-options-menu" },
    { menu: "sorting-options", button: "sorting-options-menu" },
    { menu: "filter-options", button: "filter-options-menu" },
    { menu: "round-options", button: "round-options-menu" },
];

const showClasses = ["transform", "opacity-100", "scale-100"];
const hideClasses = ["opacity-0", "scale-95", "pointer-events-none"];

menus.forEach(({ menu, button }) => {
    const menuElement = document.getElementById(menu);
    const buttonElement = document.getElementById(button);

    if (!menuElement || !buttonElement) return;

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

async function claimInvestor(email, id) {
    const csrfToken = document.getElementById("csrf_token").value;
    try {
        const response = await fetch(`/claim-investor/${id}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({ email: email }),
        });
        if (!response.ok) {
            console.log("Error:", response.statusText);
        } else {
            window.location.reload();
        }
    } catch (error) {
        console.error("Error:", error);
    }
}
