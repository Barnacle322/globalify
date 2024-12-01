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
    emits: ["all-notifications-read", "closenotifications"],
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
                this.$emit("closenotifications");
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
            this.$emit("close-aside");
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
    emits: ["investor-bookmarked", "firm-bookmarked", "company-bookmarked", "closebookmarks"],
    watch: {
        selectedTab(newVal, oldVal) {
            if (newVal === oldVal) {
                return;
            }

            if (newVal === "investor") {
                this.$refs.investor.setAttribute("data-selected", "true");
                this.$refs.investment_firm.setAttribute("data-selected", "false");
                this.$refs.company.setAttribute("data-selected", "false");
            } else if (newVal === "investment_firm") {
                this.$refs.investor.setAttribute("data-selected", "false");
                this.$refs.investment_firm.setAttribute("data-selected", "true");
                this.$refs.company.setAttribute("data-selected", "false");
            } else if (newVal === "company") {
                this.$refs.investor.setAttribute("data-selected", "false");
                this.$refs.investment_firm.setAttribute("data-selected", "false");
                this.$refs.company.setAttribute("data-selected", "true");
            }
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
    },
    async mounted() {
        await this.setupInfinteScroll();
        window.addEventListener("click", this.closeRemoveBookmark);
        window.addEventListener("click", this.closeDropdownOutside);
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
            selectedTab: "investor",
            observer: null,
            loading: false,
            reachedEnd: false,
            page: 2,
        };
    },
});

const NavbarComponent = defineComponent({
    template: "#navbar-template",
    emits: ["open-aside", "open-notifications", "bookmarked"],
    components: {
        Bookmark,
        NotificationComponent,
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
        closeNotifications(event) {
            if (this.ignoreNextOutsideClickNotifications) {
                this.ignoreNextOutsideClickNotifications = false;
                return;
            } else if (event && this.$refs.notifications && !this.$refs.notifications.$el.contains(event.target)) {
                this.notificationsOpened = false;
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
        window.addEventListener("click", this.closeNotifications);
        if (!document.hidden) {
            this.startPolling();
        }
        document.addEventListener("visibilitychange", this.handleVisibilityChange);
    },
    beforeUnmount() {
        window.removeEventListener("click", this.closeBookmark);
        window.removeEventListener("click", this.closeNotifications);
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    },
    data() {
        return {
            bookmarksOpened: false,
            ignoreNextOutsideClickBookmarks: false,
            notificationsOpened: false,
            ignoreNextOutsideClickNotifications: false,
            notifications: [],
        };
    },
});

const FullInvestor = defineComponent({
    template: "#full-investor-template",
    props: { slug: String, rendercontacts: Boolean },
    emits: ["close-investor", "bookmarked"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteInvestorParam();
        document.removeEventListener("click", this.handleClickOutside);
        const script_element = document.getElementById("twitter-script");
        if (script_element) script_element.remove();
    },
    created() {
        this.fetchInvestor();
        window.removeEventListener("popstate", this.checkUrlParams);
    },
    methods: {
        deleteInvestorParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("investor");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("investor");
            if (!investorSlug) {
                this.$emit("close-investor");
            }
        },
        async fetchInvestor() {
            try {
                const response = await fetch(`/investor/${this.slug}/get`);
                if (response.ok) {
                    const data = await response.json();
                    this.investor = data.investor;
                    this.isBookmarked = data.isBookmarked;
                    this.unpaid = data.unpaid;
                    await this.loadTwitterTimeline();
                } else {
                    this.closeInvestor();
                    return;
                }
            } catch (error) {
                console.error("Error fetching investor:", error);
                this.closeInvestor();
            } finally {
                this.isLoading = false;
            }
        },
        async loadTwitterTimeline() {
            if (!this.investor?.twitter) return;
            this.loadingTwitter = true; // Set loading state to true
            this.ensureTwitterScriptLoaded(() => {
                const timeline = document.querySelector(".twitter-timeline");
                if (timeline) {
                    timeline.innerHTML = "";
                    timeline.setAttribute("href", this.investor.twitter);
                    window.twttr?.widgets.load();

                    const observer = new MutationObserver((mutations) => {
                        mutations.forEach((mutation) => {
                            const twitterWidget = document.querySelector("[id^='twitter-widget-']");
                            if (twitterWidget && twitterWidget.offsetHeight > 0) {
                                this.loadingTwitter = false;
                                observer.disconnect();
                            }
                        });
                    });

                    observer.observe(document.body, { childList: true, subtree: true });
                }
            });
        },
        ensureTwitterScriptLoaded(callback) {
            const script_element = document.getElementById("twitter-script");
            if (script_element) script_element.remove();

            if (!this.twitterScriptLoaded) {
                const script = document.createElement("script");
                script.src = "https://platform.twitter.com/widgets.js";
                script.id = "twitter-script";
                script.async = true;
                script.onload = () => {
                    this.twitterScriptLoaded = true;
                    callback();
                };
                document.body.appendChild(script);
            } else {
                callback();
            }
        },
        async toggleBookmark(investorId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investor/${investorId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    const data = await response.json();
                    var svg = document.getElementById(`bookmark-svg-investor-${investorId}`);
                    if (data[0].bookmarked) {
                        this.$emit("bookmarked", { investorId: investorId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        // svg.style.fill = "none";
                        this.$emit("bookmarked", { investorId: investorId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-investor");
            }
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        closeInvestor() {
            this.$emit("close-investor");
        },
        getTwitterHandle(url) {
            return url.split("/").pop();
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            showPopover: false,
            isExpanded: false,
            isLoading: true,
            isBookmarked: false,
            investor: null,
            unpaid: false,
            dropdownOpened: false,
            twitterScriptLoaded: false,
            loadingTwitter: false,
        };
    },
});

const FullInvestmentFirm = defineComponent({
    template: "#full-investment-firm-template",
    props: ["slug"],
    emits: ["close-investment-firm", "bookmarked"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteInvestmentFirmParam();
        document.removeEventListener("click", this.handleClickOutside);
    },
    created() {
        this.fetchInvestmentFirm();
        window.removeEventListener("popstate", this.checkUrlParams);
    },
    methods: {
        async fetchInvestmentFirm() {
            this.isLoading = true;
            try {
                const response = await fetch(`/investment-firm/${this.slug}`);
                if (response.ok) {
                    const data = await response.json();
                    this.investmentFirm = data.investment_firm;
                    this.unpaid = data.unpaid;
                    this.isBookmarked = data.isBookmarked;
                } else {
                    this.closeInvestmentFirm();
                    return;
                }
            } catch (error) {
                console.error("Error fetching investment firm:", error);
            } finally {
                this.isLoading = false;
            }
        },
        async toggleBookmark(firmId) {
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
                    const data = await response.json();
                    var svg = document.getElementById(`bookmark-svg-firm-${firmId}`);
                    if (data[0].bookmarked) {
                        this.$emit("bookmarked", { firmId: firmId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        this.$emit("bookmarked", { firmId: firmId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        getTwitterHandle(url) {
            if (!url) return;
            return url.split("/").pop();
        },
        deleteInvestmentFirmParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("investment-firm");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("investment-firm");
            if (!investorSlug) {
                this.$emit("close-investment-firm");
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-investment-firm");
            }
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        сloseInvestmentFirm() {
            this.$emit("close-investment-firm");
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            investmentFirm: null,
            isBookmarked: false,
            unpaid: false,
            dropdownOpened: false,
        };
    },
});

const FullCompany = defineComponent({
    template: "#full-company-template",
    props: ["slug"],
    emits: ["close-company", "bookmarked"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteCompanyParam();
        document.removeEventListener("click", this.handleClickOutside);
    },
    created() {
        this.fetchCompany();
        window.removeEventListener("popstate", this.checkUrlParams);
    },
    methods: {
        deleteCompanyParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("company");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("company");
            if (!investorSlug) {
                this.$emit("close-company");
            }
        },
        async fetchCompany() {
            this.isLoading = true;
            try {
                const response = await fetch(`/company/${this.slug}`);
                if (response.ok) {
                    const data = await response.json();
                    this.company = data.company;
                    this.unpaid = data.unpaid;
                    this.isBookmarked = data.isBookmarked;
                } else {
                    this.closeCompany();
                    return;
                }
            } catch (error) {
                console.error("Error fetching company:", error);
            } finally {
                this.isLoading = false;
            }
        },
        async toggleBookmark(companyId) {
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
                    const data = await response.json();
                    var svg = document.getElementById(`bookmark-svg-company-${companyId}`);
                    if (data[0].bookmarked) {
                        this.$emit("bookmarked", { companyId: companyId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        svg.style.fill = "none";
                        this.$emit("bookmarked", { companyId: companyId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-company");
            }
        },
        getTwitterHandle(url) {
            if (!url) return;
            return url.split("/").pop();
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        closeCompany() {
            this.$emit("close-company");
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            isBookmarked: false,
            company: null,
            unpaid: false,
            dropdownOpened: false,
        };
    },
});

const SearchHistory = defineComponent({
    template: "#search-history-template",
    delimiters: ["[[", "]]"],
    props: ["type"],
    async mounted() {
        try {
            const response = await fetch(`/search-history?type=${this.type}&page=1&limit=5`);
            if (response.ok) {
                const data = await response.json();
                for (let item of data) {
                    this.searchHistoryData.push(...item.histories);
                }
            } else {
                console.error("An error occurred while fetching the search history.");
            }
        } catch (error) {
            console.error(error);
        }
    },
    data() {
        return {
            searchHistoryData: [],
        };
    },
});
