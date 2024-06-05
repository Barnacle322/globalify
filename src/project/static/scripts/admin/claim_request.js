function approveClaimRequest(id) {
    const csrfToken = document.getElementById("csrf_token").value;

    fetch(`/admin/claim-request/${id}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ status: "approved" }),
    })
        .then((response) => {
            if (response.ok) {
                window.location.reload();
            }
        })
        .catch((error) => console.error("Error approving claim request:", error));
}

function rejectClaimRequest(id) {
    const csrfToken = document.getElementById("csrf_token").value;

    fetch(`/admin/claim-request/${id}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ status: "rejected" }),
    })
        .then((response) => {
            if (response.ok) {
                window.location.reload();
            }
        })
        .catch((error) => console.error("Error denying claim request:", error));
}
