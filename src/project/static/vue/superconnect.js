const SessionRequestComponent = defineComponent({
    template: "#session-request-template",
    props: ["expertId"],
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
    methods: {
        async bookSession() {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/superconnect/book-session/${this.expertId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                console.log("Booking response:", response);
            } catch (error) {
                console.error("Error booking session:", error);
            }
        },
        closeSession() {
            this.$emit("close-session");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeSession();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeSession();
            }
        },
    },
    data() {
        return {};
    },
});

const FullExpertComponent = defineComponent({
    template: "#full-expert-template",
    props: ["expertId"],
    async mounted() {
        await this.fetchExpert(this.expertId);
        window.addEventListener("keydown", this.handleKeyDown);
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
    },
    async created() {
        await this.fetchExpert(this.expertId);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },
    methods: {
        async fetchExpert(expertId) {
            try {
                const response = await fetch(`/superconnect/expert/${expertId}`);
                if (!response.ok) {
                    throw new Error("Failed to fetch expert data");
                }
                const data = await response.json();
                this.expert = data.expert;
                console.log("Expert data:", this.expert.picture_url);
            } catch (error) {
                console.error("Error fetching expert data:", error);
            }
        },
        closeModal() {
            this.showModal = false;
        },
        closeExpert() {
            this.$emit("close-expert");
        },
        confirmBooking() {
            // Handle booking confirmation logic here
            console.log("Booking confirmed for:", this.selectedTimeslot);
            this.closeModal();
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        formatDate(dateString) {
            if (!dateString) return null;
            const date = new Date(dateString);
            if (isNaN(date)) return dateString;
            return date.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
        },
        getExperienceYears(qualifications) {
            if (!qualifications || !qualifications.length) return 0;

            // Find earliest start date
            let earliestDate = new Date();
            qualifications.forEach((qual) => {
                if (qual.start_date) {
                    const startDate = new Date(qual.start_date);
                    if (!isNaN(startDate) && startDate < earliestDate) {
                        earliestDate = startDate;
                    }
                }
            });

            // Calculate years of experience
            const now = new Date();
            const years = now.getFullYear() - earliestDate.getFullYear();
            return years > 0 ? years : "<1";
        },
        getQualificationColorClass(type) {
            const classes = {
                EDUCATION: "bg-gradient-to-b from-blue-500 to-indigo-600",
                WORK: "bg-gradient-to-b from-indigo-500 to-purple-600",
                CERTIFICATE: "bg-gradient-to-b from-green-500 to-teal-600",
                AWARD: "bg-gradient-to-b from-amber-500 to-orange-600",
                OTHER: "bg-gradient-to-b from-gray-500 to-slate-600",
            };

            return classes[type] || classes["OTHER"];
        },
        getCurrentPosition(positionId) {
            // Replace with your actual implementation to fetch position by ID
            // For now, return a placeholder
            return "Current Position";
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeExpert();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeExpert();
            }
        },
    },
    data() {
        return {
            selectedTimeslot: null,
            selectedDate: null,
            showModal: false,
            isLoading: false,
            isExpanded: false,
            expert: null,
        };
    },
});

const SessionInfoComponent = defineComponent({
    template: "#session-info-template",
    props: {
        session: {
            type: Object,
            required: true,
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
    methods: {
        async processAction(session, action) {
            try {
                const csrf_token = document.getElementById("csrf_token").value;

                const response = await fetch("/superconnect/session/action/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                    body: JSON.stringify({
                        session_id: session.id,
                        action: action,
                    }),
                });

                const data = await response.json();
                if (data.error) {
                    console.error("Error changing session status:", data.error);
                    return;
                }

                const actionMap = {
                    approve: "upcoming",
                    cancel: "canceled",
                    delete: "deleted",
                };
                if (action === "delete") {
                    this.$parent.sessions = this.$parent.sessions.filter((s) => s.id !== session.id);
                } else {
                    session.status = actionMap[action] || session.status;
                    session.confirmRequested = false;
                }

                this.$emit("close");

                this.$nextTick(() => {
                    this.$parent.sessions = [...this.$parent.sessions];
                });
            } catch (error) {
                console.error("Action failed:", error);
                return;
            }
        },
        formatDate(dateString) {
            return new Date(dateString).toLocaleDateString("en-US", {
                year: "numeric",
                month: "long",
                day: "numeric",
            });
        },
        formatTime(timeString) {
            return new Date(`1970-01-01T${timeString}`).toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
            });
        },
        closeSessionInfo() {
            this.$emit("close-session-info");
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeSessionInfo();
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeSessionInfo();
            }
        },
    },
    data() {
        return {
            statusClasses: {
                pending: "bg-yellow-100 text-yellow-800",
                upcoming: "bg-green-100 text-green-800",
                past: "bg-gray-100 text-gray-800",
                canceled: "bg-red-100 text-red-800",
            },
            statusText() {
                switch (this.session.status) {
                    case "pending":
                        return "Awaiting Approval";
                    case "upcoming":
                        return "Upcoming";
                    case "past":
                        return "Completed";
                    case "canceled":
                        return "Canceled";
                    default:
                        return this.session.status;
                }
            },
        };
    },
});

const SessionComponent = defineComponent({
    template: "#session-template",
    computed: {
        filteredSessions() {
            if (!this.sessions.length) return null;
            const now = new Date();
            return this.types
                .filter((type) => this.filters[type])
                .map((type) => {
                    const sessions = this.sessions.filter((session) => {
                        return this.getSessionType(session) === type;
                    });
                    const sortedSessions = this.sortSessions(sessions);
                    return sessions.length ? { type, title: this.config[type].title, sessions: sortedSessions } : null;
                })
                .filter(Boolean);
        },
    },
    mounted() {
        this.fetchSessions();
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        document.removeEventListener("click", this.handleClickOutside);
    },
    methods: {
        async fetchSessions() {
            try {
                const response = await fetch("/superconnect/get_sessions/");
                if (!response.ok) {
                    throw new Error("Failed to fetch sessions");
                }
                const { sessions } = await response.json();
                this.sessions = sessions.map((session) => ({
                    ...session,
                    confirmRequested: false,
                }));
            } catch (error) {
                console.error("Error fetching sessions:", error);
                this.sessions = [];
            }
        },
        sortSessions(sessions) {
            return [...sessions].sort((a, b) => {
                const dateA = new Date(a.created_at);
                const dateB = new Date(b.created_at);
                return this.sortOrder === "newest" ? dateB - dateA : dateA - dateB;
            });
        },
        getSessionType(session) {
            if (session.status === "pending") return "pending";
            if (session.status === "upcoming") return "upcoming";
            if (session.status === "past" || session.status === "canceled") return "past";
            return null;
        },
        formatDate(dateString) {
            return new Date(dateString).toLocaleDateString("en-US", {
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric",
            });
        },
        formatTime(dateString) {
            return new Date(dateString).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
        },
        toggleSortOrder() {
            this.sortOrder = this.sortOrder === "newest" ? "oldest" : "newest";
        },
        toggleFilter(type) {
            this.filters[type] = !this.filters[type];
        },
        async processAction(session, actionConfig) {
            try {
                const csrf_token = document.getElementById("csrf_token").value;
                const response = await fetch("/superconnect/session/action/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                    body: JSON.stringify({
                        session_id: session.id,
                        action: actionConfig.nextStatus,
                    }),
                });

                data = await response.json();
                if (data.error) {
                    console.error("Error changing session status:", data.error);
                    return;
                }

                session.status = actionConfig.nextStatus;
                session.confirmRequested = false;

                this.$nextTick(() => {
                    this.sessions = [...this.sessions];
                });
            } catch (error) {
                console.error("Action failed:", error);
                return;
            }
        },
        async handleAction(session, groupType) {
            const actionConfig = this.config[groupType];
            if (!session.confirmRequested) {
                session.confirmRequested = true;
            } else {
                await this.processAction(session, actionConfig);
            }
        },
        resetConfirm(session) {
            session.confirmRequested = false;
        },
        getButtonColor(session, groupType) {
            return session.confirmRequested ? this.config[groupType].confirmColor : this.config[groupType].baseColor;
        },
        handleClickOutside(event) {
            const dropdown = this.$refs.dropdownContainer;
            if (dropdown && !dropdown.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            sessions: [],
            filters: { pending: true, upcoming: true, past: true },
            types: ["pending", "upcoming", "past"],
            config: {
                pending: {
                    title: "Awaiting Approval",
                    defaultText: "Approve",
                    confirmText: "Sure?",
                    baseColor: "#3b82f6",
                    confirmColor: "#22c55e",
                    nextStatus: "upcoming",
                },
                upcoming: {
                    title: "Upcoming Sessions",
                    defaultText: "Cancel",
                    confirmText: "Sure?",
                    baseColor: "#22c55e",
                    confirmColor: "#ef4444",
                    nextStatus: "past",
                },
                past: {
                    title: "Past Sessions",
                    defaultText: "Delete",
                    confirmText: "Sure?",
                    baseColor: "#ef4444",
                    confirmColor: "#b91c1c",
                    nextStatus: null,
                },
            },
            sortOrder: "newest",
            dropdownOpened: false,
        };
    },
});

createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        FullExpertComponent,
        SessionRequestComponent,
        SessionComponent,
        SessionInfoComponent,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    mounted() {
        document.addEventListener("click", this.handleClickOutside);
        this.asideMinified = localStorage.getItem("asideMinified") == "true";
    },
    methods: {
        async fetchTimeslots() {
            try {
                const response = await fetch("/superconnect/fake-slots");
                if (!response.ok) {
                    throw new Error("Failed to fetch timeslots");
                }
                const data = await response.json();
                this.timeslots = data;
            } catch (error) {
                console.error("Error fetching timeslots:", error);
            }
        },
        openExpert(expertId) {
            this.isFullExpertOpened = true;
            this.selectedExpertId = expertId;
        },
        openSessionRequest(expertId) {
            this.isSessionRequestOpened = true;
            this.selectedExpertId = expertId;
        },
        openSessionInfo(session) {
            this.isSessionInfoOpened = true;
            this.selectedSession = session;
        },
    },
    data() {
        return {
            timeslots: [],
            asideMinified: false,
            asideExpanded: true,
            selectedExpertId: null,
            isSessionRequestOpened: false,
            isFullExpertOpened: false,
            isSessionInfoOpened: false,
            selectedSession: null,
        };
    },
}).mount("#app");
