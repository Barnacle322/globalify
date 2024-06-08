document.addEventListener("DOMContentLoaded", function () {
    const csrfToken = document.getElementById("csrf_token").value;
    const form = document.getElementById("claimForm");
    const email = document.getElementById("email");
    const slug = form.getAttribute("data-slug");

    form.addEventListener("submit", function (event) {
        const recaptchaValue = grecaptcha.getResponse();
        if (recaptchaValue.length === 0) {
            event.preventDefault();
            alert("Please verify that you are not a robot.");
            return;
        }

        fetch(`/investor/${slug}/claiming-email`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({ email: email.value }),
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
});

document.addEventListener("DOMContentLoaded", function () {
    const csrfToken = document.getElementById("csrf_token").value;
    const form = document.getElementById("verifyForm");
    const email = document.getElementById("email");
    const code = document.getElementById("code");
    const slug = form.getAttribute("data-slug");

    form.addEventListener("submit", function () {
        fetch(`/investor/${slug}/claim`, {
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
                } else if (!response.ok) {
                    alert("There has been a problem with your request.");
                }
            })
            .catch((error) => {
                console.error("There has been a problem with your fetch operation:", error);
            });
    });
});
