document.addEventListener("DOMContentLoaded", function () {
    const csrfToken = document.getElementById("csrf_token").value;
    const form = document.getElementById("claimForm");
    const emailInput = document.getElementById("email");
    const slug = form.getAttribute("data-slug");

    form.addEventListener("submit", function (event) {
        const recaptchaValue = grecaptcha.getResponse();
        if (recaptchaValue.length === 0) {
            event.preventDefault();
            alert("Please verify that you are not a robot.");
            return;
        }

        fetch(`/investor/${slug}/claim/manual`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({ email: emailInput.value }),
        }).then((response) => {
            if (response.redirected) {
                window.location.href = response.url;
            } else if (!response.ok) {
                alert("There has been a problem with your request.");
            }
        });
    });
});
