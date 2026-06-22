const csrfToken = document.getElementById("csrf_token").value;
const form = document.getElementById("claimForm");
const email = document.getElementById("email");
const slug = form.getAttribute("slug");

form.addEventListener("submit", function (event) {
    event.preventDefault();

    const capTokenInput = form.querySelector('input[name="cap-token"]');
    const capToken = capTokenInput ? capTokenInput.value : null;

    const payload = { email: email.value };
    if (capToken) payload["cap-token"] = capToken;

    fetch(`/investor/${slug}/claim/email`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(payload),
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
