function markNotificationAsRead() {

    const button = document.querySelector('.ms-auto[data-dismiss-target="#toast-interactive"]');

    const notificationId = button.getAttribute('data-notification-id');

    const csrfToken = document.getElementById("csrf_token").value;

    fetch(`/notification/edit/${notificationId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
    })
    .then(response => {
        if (response.ok) {
            console.log('Notification marked as read');
            button.parentNode.parentNode.classList.add('fade-out-down');
        } else {
            console.error('Failed to mark notification as read');
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

