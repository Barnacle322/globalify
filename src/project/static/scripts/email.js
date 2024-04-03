function showEmailField() {
    document.getElementById("email_input").classList.remove("hidden");
    document.getElementById("email_input").classList.add("flex");
    document.getElementById("notification_button").classList.add("hidden");
}

document.getElementById("email_input").addEventListener("submit", function (event) {
    event.preventDefault();
    submitEmail();
});

function makeSubmission() {
    var field = document.getElementById("email");
    field.classList.add("hidden");
    field.classList.remove("flex");

    var button = document.getElementById("submit-button");
    button.classList.add("w-full", "items-center", "cursor-not-allowed");
    button.disabled = "disabled";
    button.innerHTML = "Applied!";

    return field.value;
}

function apiCall(map) {
    const csrfToken = document.getElementById("csrf_token").value;

    const response = fetch("/waitlist-email", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(Object.fromEntries(map)),
    })
        .then((response) => response.json())
        .then((data) => {
            console.log("Success:", data);
        })
        .catch((error) => {
            console.error("Error:", error);
        });

    return response;
}

function submitEmail() {
    var email_map = new Map();
    email_map.set("email", makeSubmission());
    response = apiCall(email_map);
    console.log(response);
}
