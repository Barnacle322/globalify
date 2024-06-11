document.addEventListener("DOMContentLoaded", function () {
    const csrfToken = document.getElementById("csrf_token").value;
    const form = document.getElementById("claimForm");
    const email = document.getElementById("email");
    const slug = form.getAttribute("data-slug");

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

        fetch(`/investor/${slug}/claim/email`, {
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

    form.addEventListener("submit", function (event) {
        event.preventDefault();

        fetch(`/investor/${slug}/claim/email/verify`, {
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
});
