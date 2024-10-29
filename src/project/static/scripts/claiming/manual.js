const csrfToken = document.getElementById("csrf_token").value;
const form = document.getElementById("claimForm");
const emailInput = document.getElementById("email");
const slug = form.getAttribute("slug");

form.addEventListener("submit", function (event) {
    event.preventDefault();

    const recaptcha = grecaptcha.getResponse();

    fetch(`/investor/${slug}/claim/manual`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ email: emailInput.value, recaptcha: recaptcha }),
    })
        .then((response) => {
            if (response.redirected) {
                window.location.href = response.url;
            }
        })
        .catch((error) => {
            console.error("Error:", error);
        });
});
