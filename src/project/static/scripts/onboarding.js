const usernameInput = document.getElementById("username");


usernameInput.addEventListener("blur", async (event) => {
    const username = event.target.value;
    if (!username) {
        return;
    }
    const response = await fetch(`/username/${username}`);
    const result = await response.json();
    console.log(result)

    if (result.is_taken) {
        const message = document.createElement("div");
        message.innerHTML = "Username is taken";
        message.classList.add("text-danger");
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
