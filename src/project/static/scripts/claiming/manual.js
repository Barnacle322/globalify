const csrfToken = document.getElementById("csrf_token").value;
const form = document.getElementById("claimForm");
const emailInput = document.getElementById("email");
const slug = form.getAttribute("slug");

function checkCaptcha() {
    const recaptchaValue = grecaptcha.getResponse();
    if (recaptchaValue.length === 0) {
        alert("Please verify that you are not a robot.");
        return false;
    }
    return true;
}

form.addEventListener("submit", function (event) {
    event.preventDefault();

    if (!checkCaptcha()) {
        return;
    }

    fetch(`/investor/${slug}/claim/manual`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ email: emailInput.value }),
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
