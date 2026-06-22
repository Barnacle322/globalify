const csrfToken = document.getElementById("csrf_token").value;
const form = document.getElementById("verifyForm");
const email = document.getElementById("email");
const code = document.getElementById("code");
const slug = form.getAttribute("slug");

form.addEventListener("submit", function (event) {
    event.preventDefault();

    fetch(`/firm/${slug}/claim/email/verify`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ code: code.value, email: email.value }),
    })
        .then((response) => {
            if (response.redirected) {
                window.location.href = response.url;
            }
        })
        .catch((error) => {
            console.error("There has been a problem with your fetch operation:", error);
        });
});
