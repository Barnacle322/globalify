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
    },
    async created() {
        await this.fetchExpert(this.expertId);
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

const SessionComponent = defineComponent({
    template: "#session-template",

    computed: {
        filteredSessions() {
            if (this.sessions.length == 0) return null;

            const now = new Date();
            console.log(now);
            const groups = {
                pending: {
                    type: "pending",
                    title: "Awaiting Approval",
                    sessions: [],
                },
                upcoming: {
                    type: "upcoming",
                    title: "Upcoming Sessions",
                    sessions: [],
                },
                past: {
                    type: "past",
                    title: "Past Sessions",
                    sessions: [],
                },
            };

            this.sessions.forEach((session) => {
                const sessionDate = new Date(session.created_at);
                if (session.status === "pending" && this.filters.pending) {
                    groups.pending.sessions.push(session);
                } else if (session.status === "upcoming" && sessionDate > now && this.filters.upcoming) {
                    groups.upcoming.sessions.push(session);
                } else if ((session.status === "past" || session.status === "canceled") && this.filters.past) {
                    groups.past.sessions.push(session);
                }
            });

            return this.filterOrder
                .filter((type) => this.filters[type])
                .map((type) => groups[type])
                .filter((group) => group.sessions.length > 0);
        },
    },
    mounted() {
        this.fetchSessions();
    },
    methods: {
        async fetchSessions() {
            try {
                const response = await fetch(`/superconnect/get_sessions/`);
                if (!response.ok) throw new Error("Failed to fetch sessions");
                const { sessions } = await response.json();
                this.sessions = sessions.map((session) => ({
                    ...session,
                    approveConfirmed: false,
                    cancelConfirmed: false,
                    deleteConfirmed: false,
                }));
                console.log(this.sessions);
            } catch (error) {
                console.error("Error fetching sessions:", error);
                this.sessions = [];
            }
        },
        formatDate(dateString) {
            const options = { weekday: "long", day: "numeric", month: "long", year: "numeric" };
            return new Date(dateString).toLocaleDateString("en-US", options);
        },
        formatTime(dateString) {
            return new Date(dateString).toLocaleTimeString("en-US", {
                hour: "2-digit",
                minute: "2-digit",
            });
        },
        toggleApproveConfirm(session) {
            session.approveConfirmed = !session.approveConfirmed;
            if (session.approveConfirmed) {
            }
        },
        toggleCancelConfirm(session) {
            session.cancelConfirmed = !session.cancelConfirmed;
            if (session.cancelConfirmed) {
            }
        },
        toggleDeleteConfirm(session) {
            session.deleteConfirmed = !session.deleteConfirmed;
            if (session.deleteConfirmed) {
            }
        },
        resetConfirmation(session, config) {
            // Таймер для плавного перехода
            setTimeout(() => {
                if (config.type === "pending") session.approveConfirmed = false;
                if (config.type === "upcoming") session.cancelConfirmed = false;
                if (config.type === "past") session.deleteConfirmed = false;
            }, 300); // Задержка для предотвращения мгновенного сброса
        },
        handleAction(session, config) {
            // Переключение состояния только при клике
            config.action(session);

            // Автоматический сброс через 2 секунды если не подтверждено
            if (!session[config.confirmKey]) {
                this.autoResetTimer = setTimeout(() => {
                    session[config.confirmKey] = false;
                }, 2000);
            }
        },
    },
    data() {
        return {
            sessions: [],
            filters: {
                pending: true,
                upcoming: true,
                past: true,
            },
            filterOrder: ["pending", "upcoming", "past"],
            buttonConfigs: {
                pending: {
                    type: "pending",
                    action: "approve",
                    defaultText: "Approve",
                    confirmText: "Sure?",
                    confirmKey: "approveConfirmed",
                    baseClasses: "bg-transparent",
                    hoverClasses: "hover:bg-gradient-to-r hover:from-transparent hover:to-sky-500",
                    confirmClasses: "hover:bg-gradient-to-r hover:from-transparent hover:to-green-500",
                },
                upcoming: {
                    type: "upcoming",
                    action: "cancel",
                    defaultText: "Cancel",
                    confirmText: "Sure?",
                    confirmKey: "cancelConfirmed",
                    baseClasses: "bg-transparent",
                    hoverClasses: "hover:bg-gradient-to-r hover:from-transparent hover:to-green-500",
                    confirmClasses: "hover:bg-gradient-to-r hover:from-transparent hover:to-red-500",
                },
                past: {
                    type: "past",
                    action: "delete",
                    defaultText: "Delete",
                    confirmText: "Sure?",
                    confirmKey: "deleteConfirmed",
                    baseClasses: "bg-transparent",
                    hoverClasses: "hover:bg-gradient-to-r hover:from-transparent hover:to-red-500",
                    confirmClasses: "hover:bg-gradient-to-r hover:from-transparent hover:to-red-700",
                },
            },
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
    },
    data() {
        return {
            timeslots: [],
            asideMinified: false,
            asideExpanded: true,
            selectedExpertId: null,
            isSessionRequestOpened: false,
            isSessionOpened: true,
            isFullExpertOpened: false,
        };
    },
}).mount("#app");
