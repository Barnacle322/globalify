async function deleteInvestmentFirm(id) {
    const csrfToken = document.getElementById("csrf_token").value;

    if (!confirm("Are you sure you want to delete this investment firm?")) {
        return;
    }

    const response = await fetch(`/admin/investment-firm/${id}/delete`, {
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
