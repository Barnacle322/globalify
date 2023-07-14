document.getElementById("form").addEventListener("submit", function (event) {
    event.preventDefault(); // Prevent the default form submission
    submit_email();
});

function makeSubmission() {
    var field = document.getElementById("email");
    field.classList.add("hidden");
    field.classList.remove("flex");

    var button = document.getElementById("submit-button");
    button.classList.add("w-full", "items-center");
    button.classList.remove("w-[97px]", "items-end");
    button.disabled = "disabled";
    button.innerHTML = "Subscribed!";

    return field.value;
}

function apiCall(map) {
    const response = fetch("/newsletter", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
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

function submit_email() {
    var email_map = new Map();
    email_map.set("email", makeSubmission());
    response = apiCall(email_map);
    console.log(response);
}
