const { defineComponent, createApp } = Vue;

const CreateNotableInvestmentComponent = defineComponent({
    template: "#create-notable-investment-template",
    methods: {
        closeCreateNotableInvestmentModal() {
            this.$emit("close-create-notable-investment-modal");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeCreateNotableInvestmentModal();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeCreateNotableInvestmentModal();
            }
        },
        async createNotableInvestment() {
            const csrfToken = document.getElementById("csrf_token").value;
            const name = document.getElementById("name").value;

            try {
                const response = await fetch("/admin/create/notable-investment", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ name }),
                });
                if (response.ok) {
                    const data = await response.json();
                    this.$emit("notable-investment-created", data.notable_investment.name);
                    this.closeCreateNotableInvestmentModal();
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
    },
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },
});

const NotificationComponent = defineComponent({
    template: "#notifications-template",
    emits: ["all-notifications-read", "close"],
    watch: {
        selectedTab(newVal, oldVal) {
            if (newVal === oldVal) {
                return;
            }

            if (newVal === "inbox") {
                this.$refs.inbox.setAttribute("data-selected", "true");
                this.$refs.archive.setAttribute("data-selected", "false");
            } else {
                this.$refs.inbox.setAttribute("data-selected", "false");
                this.$refs.archive.setAttribute("data-selected", "true");
            }
            this.page = 2;
            this.setupInfinteScroll();
        },
    },
    methods: {
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close");
            }
        },
        timeDifference(current, previous) {
            let msPerMinute = 60 * 1000;
            let msPerHour = msPerMinute * 60;
            let msPerDay = msPerHour * 24;
            let msPerMonth = msPerDay * 30;
            let msPerYear = msPerDay * 365;

            let elapsed = current - previous;

            if (elapsed < msPerMinute) {
                const seconds = Math.round(elapsed / 1000);
                return seconds + (seconds === 1 ? " second ago" : " seconds ago");
            } else if (elapsed < msPerHour) {
                const minutes = Math.round(elapsed / msPerMinute);
                return minutes + (minutes === 1 ? " minute ago" : " minutes ago");
            } else if (elapsed < msPerDay) {
                const hours = Math.round(elapsed / msPerHour);
                return hours + (hours === 1 ? " hour ago" : " hours ago");
            } else if (elapsed < msPerMonth) {
                const days = Math.round(elapsed / msPerDay);
                return days + (days === 1 ? " day ago" : " days ago");
            } else if (elapsed < msPerYear) {
                const months = Math.round(elapsed / msPerMonth);
                return months + (months === 1 ? " month ago" : " months ago");
            } else {
                const years = Math.round(elapsed / msPerYear);
                return years + (years === 1 ? " year ago" : " years ago");
            }
        },
        async setupInfinteScroll() {
            if (this.selectedTab === "inbox") {
                const response = await fetch("/notifications");
                if (response.ok) {
                    const data = await response.json();
                    this.notifications = data.notifications.filter((notification) => !notification.is_read);
                }
            } else if (this.selectedTab === "archive") {
                const response = await fetch("/notifications/archived");
                if (response.ok) {
                    const data = await response.json();
                    this.notifications = data.notifications.map((notification) => notification);
                }
            }
            const options = {
                root: null,
                rootMargin: "0px",
                threshold: 0.5,
            };
            const sentinel = document.getElementById("notification-sentinel");
            this.observer = new IntersectionObserver((entries, observer) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        this.reachedEnd = true;
                        this.loadMoreNotifications();
                    }
                });
            }, options);
            this.observer.observe(sentinel);
        },
        async loadMoreNotifications() {
            if (this.loading) return;
            if (!this.loading && this.reachedEnd) {
                this.loading = true;
                try {
                    let response;
                    if (this.selectedTab === "inbox") {
                        response = await fetch(`/notifications?page=${this.page}`);
                    } else if (this.selectedTab === "archive") {
                        response = await fetch(`/notifications/archived?page=${this.page}`);
                    }

                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    if (response.ok) {
                        const data = await response.json();
                        this.notifications.push(...data.notifications);
                        this.page++;
                    } else {
                        console.error("Error fetching notifications:", response.statusText);
                    }
                } catch (error) {
                    console.error("Error fetching notifications:", error.message);
                } finally {
                    this.loading = false;
                }
            }
        },
        async markAllAsRead() {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch("/notifications/mark-all-read", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                this.notifications.forEach((notification) => {
                    notification.is_read = true;
                });
                this.notifications = [];
                this.inboxNotifications = [];
                this.$emit("all-notifications-read");
            } catch (e) {
                console.error("Error marking all notifications as read:", e);
            }
        },
        async markNotificationAsRead(notificationId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch(`/notification/mark-read/${notificationId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                return response;
            } catch (e) {
                console.error("Error marking notification as read:", e);
                return null;
            }
        },
        async markAsReadWithRedirect(notificationId) {
            const response = await this.markNotificationAsRead(notificationId);
            if (response && response.redirected) {
                window.location.href = response.url;
            } else if (response && !response.ok) {
                console.error("An error occurred while marking the notification as read.");
            } else {
                this.updateNotificationsState(notificationId);
            }
        },
        async markAsRead(notificationId) {
            const response = await this.markNotificationAsRead(notificationId);
            if (response && response.ok) {
                this.updateNotificationsState(notificationId);
            } else if (response) {
                console.error("An error occurred while marking the notification as read.");
            }
        },
        updateNotificationsState(notificationId) {
            this.notifications = this.notifications.filter((notification) => notification.id !== notificationId);
            this.inboxNotifications = this.inboxNotifications.filter(
                (notification) => notification.id !== notificationId,
            );
        },
    },
    async mounted() {
        await this.setupInfinteScroll();
    },
    beforeUnmount() {
        this.observer.disconnect();
        window.removeEventListener("keydown", this.handleKeyDown);
    },
    data() {
        return {
            notifications: [],
            inboxNotifications: [],
            selectedTab: "inbox",
            observer: null,
            loading: false,
            reachedEnd: false,
            page: 2,
        };
    },
});

const AsideComponent = defineComponent({
    props: ["minified"],
    template: "#aside-template",
    mounted() {
        this.currentPath = window.location.pathname.split("/")[1];
        if (["suggestions", "investor", "investment-firm", "history"].includes(this.currentPath)) {
            this.currentPath = "search";
        }
    },
    data() {
        return {
            currentPath: null,
        };
    },
});

const AsideMobileComponent = defineComponent({
    template: "#aside-mobile-template",
    props: ["minified"],
    methods: {
        closeAside() {
            this.$emit("close");
        },
    },
    mounted() {
        this.currentPath = window.location.pathname.split("/")[1];
        if (["suggestions", "investor", "investment-firm", "history"].includes(this.currentPath)) {
            this.currentPath = "search";
        }
    },
    data() {
        return {
            currentPath: null,
        };
    },
});

const Bookmark = defineComponent({
    template: "#bookmark-template",
    emits: ["investor-bookmarked", "firm-bookmarked", "company-bookmarked", "close"],
    watch: {
        selectedTab(newVal, oldVal) {
            if (newVal === oldVal) {
                return;
            }

            // if (newVal === "investor") {
            //     this.$refs.investor.setAttribute("data-selected", "true");
            //     this.$refs.investment_firm.setAttribute("data-selected", "false");
            // } else if (newVal === "investment_firm") {
            //     this.$refs.investment_firm.setAttribute("data-selected", "true");
            //     this.$refs.investor.setAttribute("data-selected", "false");
            // }
            this.page = 2;
            this.setupInfinteScroll();
        },
    },
    methods: {
        closeDropdownOutside() {
            this.openedDropdownId = null;
        },
        formatDate(date) {
            const options = { year: "numeric", month: "long", day: "numeric" };
            return new Date(date).toLocaleString("en-US", options);
        },
        async closeBookmark(event) {
            this.$nextTick(() => {
                if (!this.$refs.removebookmark.$el.contains(event.target)) {
                    this.bookmarksOpened = false;
                }
            });
        },
        async setupInfinteScroll() {
            if (this.selectedTab === "investor") {
                const response = await fetch("/bookmarks/investors");
                if (response.ok) {
                    data = await response.json();
                    this.bookmarks = data.bookmarks;
                }
            } else if (this.selectedTab === "investment_firm") {
                const response = await fetch("/bookmarks/investment-firms");
                data = await response.json();
                if (response.ok) {
                    this.bookmarks = data.bookmarks;
                }
            } else if (this.selectedTab === "company") {
                const response = await fetch("/bookmarks/companies");
                data = await response.json();

                if (response.ok) {
                    this.bookmarks = data.bookmarks;
                }
            }
            const options = {
                root: null,
                rootMargin: "0px",
                threshold: 0.5,
            };

            const sentinel = document.getElementById("bookmark-sentinel");
            this.observer = new IntersectionObserver((entries, observer) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        this.reachedEnd = true;
                        this.loadMoreBookmarks();
                    }
                });
            }, options);
            this.observer.observe(sentinel);
        },
        async loadMoreBookmarks() {
            if (this.loading) return;
            if (!this.loading && this.reachedEnd) {
                this.loading = true;
                try {
                    let response;
                    if (this.selectedTab === "investor") {
                        response = await fetch(`/bookmarks/investors?page=${this.page}`);
                    } else if (this.selectedTab === "investment_firm") {
                        response = await fetch(`/bookmarks/investment-firms?page=${this.page}`);
                    } else if (this.selectedTab === "company") {
                        response = await fetch(`/bookmarks/companies?page=${this.page}`);
                    }
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    if (response.ok) {
                        const data = await response.json();

                        this.bookmarks.push(...data.bookmarks);
                        this.page++;
                    } else {
                        console.error("Error fetching bookmarks:", response.statusText);
                    }
                } catch (error) {
                    console.error("Error fetching bookmarks:", error.message);
                } finally {
                    this.loading = false;
                }
            }
        },
        async unbookmarkInvestor(investorId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch(`/investor/${investorId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });

                if (response.ok) {
                    this.bookmarks = this.bookmarks.filter((investor) => investor.id !== investorId);
                    this.$emit("investor-bookmarked", { investorId: investorId, status: false });
                } else {
                    console.error("Error removing bookmark:", response.statusText);
                }
            } catch (error) {
                console.error("Error removing bookmark:", error.message);
            }
        },
        async unbookmarkInvestmentFirm(firmId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investment-firm/${firmId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });

                if (response.ok) {
                    this.bookmarks = this.bookmarks.filter((firm) => firm.id !== firmId);
                    this.$emit("firm-bookmarked", { firmId: firmId, status: false });
                } else {
                    console.error("Error removing bookmark:", response.statusText);
                }
            } catch (error) {
                console.error("Error removing bookmark:", error.message);
            }
        },
        async unbookmarkCompany(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/company/${companyId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });

                if (response.ok) {
                    this.bookmarks = this.bookmarks.filter((company) => company.id !== companyId);
                    this.$emit("company-bookmarked", { companyId: companyId, status: false });
                } else {
                    console.error("Error removing bookmark:", response.statusText);
                }
            } catch (error) {
                console.error("Error removing bookmark:", error.message);
            }
        },
        updateUrlParam(paramName, paramValue, stateKey) {
            const url = new URL(window.location.href);
            if (url.searchParams.get(paramName) !== paramValue) {
                url.searchParams.set("investor", paramValue);
                url.pathname = "/search";
                window.history.pushState({}, "", url);
            }
            this[stateKey] = paramValue;
        },
        selectInvestorSlug(investorSlug) {
            this.updateUrlParam("investor", investorSlug, "selectedInvestorSlug");
            window.location.reload();
        },
        getTwitterHandle(url) {
            if (!url) return;
            return url.split("/").pop();
        },
        checkIfCompanyExists(){
            if (this.$refs.company) {
                console.log("Company element is in the DOM.");
                this.$refs.company.setAttribute("data-selected", "true");
                this.selectedTab = "company"
            } else {
                console.log("Company element is not in the DOM.");
        }
        },
    },
    async mounted() {
        // this.checkIfCompanyExists();
        await this.setupInfinteScroll();
        window.addEventListener("click", this.closeRemoveBookmark);
        window.addEventListener("click", this.closeDropdownOutside);
        this.selectedTab = this.$refs.bookmarktabs.children[0].getAttribute("name")
    },
    beforeUnmount() {
        this.observer.disconnect();
        window.removeEventListener("click", this.closeRemoveBookmark);
        window.removeEventListener("click", this.closeDropdownOutside);
    },
    data() {
        return {
            bookmarks: [],
            openedDropdownId: null,
            selectedTab: "",
            observer: null,
            loading: false,
            reachedEnd: false,
            page: 2,
        };
    },
});

const ProfileContextMenuComponent = defineComponent({
    template: "#profile-context-menu",
    emits: ["close"],
    mounted() {
        this.getAccounts();
    },
    methods: {
        async getAccounts() {
            const response = await fetch("/profile/accounts/get");
            if (response.ok) {
                this.accounts = await response.json();
            } else {
                console.error("Fetching accounts failed:", response.statusText);
            }
        },
    },
    data() {
        return {
            accounts: [],
        };
    },
});

const NavbarComponent = defineComponent({
    template: "#navbar-template",
    emits: ["open-aside", "open-notifications", "bookmarked"],
    components: {
        Bookmark,
        NotificationComponent,
        ProfileContextMenuComponent,
    },
    methods: {
        handleBookmark(data, type) {
            if (type === "investor") {
                this.$emit("bookmarked", { investorId: data.investorId, status: data.status });
            } else if (type === "firm") {
                this.$emit("bookmarked", { firmId: data.firmId, status: data.status });
            } else if (type === "company") {
                this.$emit("bookmarked", { companyId: data.companyId, status: data.status });
            }
        },
        expandAside() {
            this.$emit("open-aside");
        },
        openBookmark() {
            this.bookmarksOpened = true;
            this.ignoreNextOutsideClickBookmarks = true;
        },
        closeBookmark(event) {
            if (this.ignoreNextOutsideClickBookmarks) {
                this.ignoreNextOutsideClickBookmarks = false;
                return;
            } else if (event && this.$refs.bookmark && !this.$refs.bookmark.$el.contains(event.target)) {
                this.bookmarksOpened = false;
            }
        },
        openNotifications() {
            this.notificationsOpened = true;
            this.ignoreNextOutsideClickNotifications = true;
        },
        close(event) {
            if (this.ignoreNextOutsideClickNotifications) {
                this.ignoreNextOutsideClickNotifications = false;
                return;
            } else if (event && this.$refs.notifications && !this.$refs.notifications.$el.contains(event.target)) {
                this.notificationsOpened = false;
            }
        },
        openProfileContextMenu() {
            this.profileContextMenuOpened = true;
            this.ignoreNextOutsideClickProfileContextMenu = true;
        },
        closeProfileContextMenu() {
            if (this.ignoreNextOutsideClickProfileContextMenu) {
                this.ignoreNextOutsideClickProfileContextMenu = false;
                return;
            } else if (
                event &&
                this.$refs.profilecontextmenu &&
                !this.$refs.profilecontextmenu.$el.contains(event.target)
            ) {
                this.profileContextMenuOpened = false;
            }
        },
        async fetchNotificationInbox() {
            try {
                const response = await fetch("/notifications");
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                this.notifications = data.notifications.map((notification) => notification);
            } catch (e) {
                console.error("Error fetching notifications:", e);
            }
        },
        handleAllNotificationsRead() {
            this.notifications.forEach((notification) => {
                notification.is_read = true;
            });
        },
        startPolling() {
            this.pollingInterval = setInterval(async () => {
                await this.fetchNotificationInbox();
            }, 15000);
        },
        stopPolling() {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        },
        handleVisibilityChange() {
            if (document.hidden) {
                this.stopPolling();
            } else {
                this.startPolling();
            }
        },
    },
    computed: {
        unreadNotifications() {
            return this.notifications.some((notification) => !notification.is_read);
        },
    },
    async mounted() {
        window.addEventListener("click", this.closeBookmark);
        window.addEventListener("click", this.close);
        window.addEventListener("click", this.closeProfileContextMenu);
        if (!document.hidden) {
            this.startPolling();
        }
        document.addEventListener("visibilitychange", this.handleVisibilityChange);

        const header = this.$refs.header;
        header.setAttribute("id", "navbar");
    },
    beforeUnmount() {
        window.removeEventListener("click", this.closeBookmark);
        window.removeEventListener("click", this.close);
        window.removeEventListener("click", this.closeProfileContextMenu);
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    },
    data() {
        return {
            bookmarksOpened: false,
            ignoreNextOutsideClickBookmarks: false,
            notificationsOpened: false,
            ignoreNextOutsideClickNotifications: false,
            ignoreNextOutsideClickProfileContextMenu: false,
            notifications: [],
            profileContextMenuOpened: false,
        };
    },
});
