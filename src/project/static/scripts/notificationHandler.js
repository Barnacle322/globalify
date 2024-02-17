async function markNotificationAsRead() {
    const button = document.querySelector('.ms-auto[data-dismiss-target="#toast-interactive"]');

    if (!button) {
        console.error("Button not found");
        return;
    }

    const notificationId = button.getAttribute("data-notification-id");

    try {
        const response = await fetch(`/notification/edit/${notificationId}`);

        if (response.ok) {
            console.log("Notification marked as read");
            button.parentNode.parentNode.classList.add("fade-out-down");
        } else {
            console.error("Failed to mark notification as read");
        }
    } catch (error) {
        console.error("Error:", error);
    }
}
