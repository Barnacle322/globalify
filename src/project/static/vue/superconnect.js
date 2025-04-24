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

createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        FullExpertComponent,
        SessionRequestComponent,
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
            isFullExpertOpened: false,
        };
    },
}).mount("#app");
