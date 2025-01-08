createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    created() {
        this.asideMinified = localStorage.getItem("asideMinified") === "true";
    },
    methods: {
        toggleVisibility(showRef, hideRef) {
            this.$refs[hideRef].classList.add("hidden");
            this.$refs[hideRef].classList.remove("flex");
            this.$refs[showRef].classList.add("flex");
            this.$refs[showRef].classList.remove("hidden");
        },
        openScheduler() {
            this.$refs.schedulerContainer.classList.add("overflow-hidden");
            this.$refs.schedulerContainer.classList.remove("hidden");
            this.$refs.scheduler.src =
                "https://calendar.google.com/calendar/appointments/schedules/AcZssZ2Mhg7yxFA9l4_9e56OuLXZs2e1R_6XGPXDLmJzY4NYBZkiLMGNMDgsK0x6_8lqlaSMQ--Cu55C?gv=true";
        },
        closeScheduler() {
            this.$refs.schedulerContainer.classList.add("hidden");
            this.$refs.scheduler.src = "";
        },
        openAnnual() {
            this.toggleVisibility("premiumAnnual", "premiumMonthly");
        },
        openMonthly() {
            this.toggleVisibility("premiumMonthly", "premiumAnnual");
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
        };
    },
}).mount("#app");
