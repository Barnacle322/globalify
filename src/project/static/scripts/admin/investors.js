function deleteInvestor(id) {
    const csrfToken = document.getElementById("csrf_token").value;

    if (!confirm("Are you sure you want to delete this investor?")) {
        return;
    }

    const response = fetch(`/admin/dashboard/investor/${id}/delete`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken,
        },
    });
    if (response.ok) {
        window.location.reload();
    }
}
