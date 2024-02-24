const usernameInput = document.getElementById("username");

usernameInput.addEventListener("blur", async (event) => {
    const username = event.target.value;
    if (!username) {
        return;
    }
    const response = await fetch(`/username/${username}`);
    const result = await response.json();

    if (result.is_taken) {
        if (usernameInput.classList.contains("is-invalid")) {
            return;
        }
        const message = document.createElement("div");
        message.innerHTML = "Username is taken";
        message.classList.add("text-red-500", "text-xs", "mt-2");
        usernameInput.parentNode.appendChild(message);
        usernameInput.classList.add("is-invalid");
    }
    if (!result.is_taken) {
        const message = usernameInput.parentNode.querySelector("div");
        if (message) {
            usernameInput.parentNode.removeChild(message);
        }
        usernameInput.classList.remove("is-invalid");
    }
});
