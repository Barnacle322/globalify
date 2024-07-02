const ConfirmRestoreComponent = defineComponent({
    template: "#confirm-restore-template",
    data() {
        return {
            investor_point_origin: {},
        };
    },
    methods: {
        closeConfirmRestore() {
            this.$emit("close-confirm-restore");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeConfirmRestore();
            }
        },
        async fetchPointOriginData() {
            try {
                const response = await fetch("/settings/investor/point-origin");
                if (!response.ok) {
                    console.error("Network response was not ok");
                }
                this.investor_point_origin = await response.json();
            } catch (error) {
                console.error("There has been a problem with your fetch operation:", error);
            }
        },
        async restorePointOrigin() {
            try {
                const response = await fetch("/settings/investor/restore", {
                    method: "GET",
                });
                if (response.redirected) {
                    window.location.href = response.url;
                }
            } catch (error) {
                console.error("There has been a problem with your fetch operation:", error);
            }
        },
    },
    computed: {
        notableInvestmentsTitles() {
            if (this.investor_point_origin && this.investor_point_origin.notable_investments) {
                return this.investor_point_origin.notable_investments.map((ni) => ni.title).join(", ");
            }
            return "";
        },
        roundsTitles() {
            if (this.investor_point_origin && this.investor_point_origin.rounds) {
                return this.investor_point_origin.rounds.map((r) => r.title).join(", ");
            }
            return "";
        },
        industriesTitles() {
            if (this.investor_point_origin && this.investor_point_origin.industries) {
                return this.investor_point_origin.industries.map((i) => i.title).join(", ");
            }
            return "";
        },
    },

    mounted() {
        this.fetchPointOriginData();
        window.addEventListener("keydown", this.handleKeyDown);
    },
    beforeUnmount() {
        this.investor_point_origin = {};
        window.removeEventListener("keydown", this.handleKeyDown);
    },
});

const InviteMemberComponent = defineComponent({
    template: "#invite-member-template",
    data() {
        return {
            email: "",
            errors: {},
            loading: false,
        };
    },
    methods: {
        closeInviteMember() {
            this.$emit("close-invite-member");
        },
        async inviteMember() {
            this.loading = true;
            this.errors = {};
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch("/invite-member", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ email: this.email }),
                });

                if (response.ok) {
                    this.$emit("close");
                } else {
                    const data = await response.json();
                    this.errors = data.errors;
                }
            } catch (error) {
                console.error("Error inviting member:", error.message);
            } finally {
                this.loading = false;
            }
        },
    },
});

createApp({
    emits: ["close-confirm-restore", "close-invite-member"],
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        Bookmark,
        ConfirmRestoreComponent,
        InviteMemberComponent,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
        confirmRestoreOpened(value) {
            if (value) {
                document.body.classList.add("overflow-hidden");
            } else {
                document.body.classList.remove("overflow-hidden");
            }
        },
        inviteMemberOpened(value) {
            if (value) {
                document.body.classList.add("overflow-hidden");
            } else {
                document.body.classList.remove("overflow-hidden");
            }
        },
    },
    created() {
        this.asideMinified = localStorage.getItem("asideMinified") === "true";
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            confirmRestoreOpened: false,
            inviteMemberOpened: false,
            csrfToken: "",
            selectedRounds: [],
            selectedIndustries: [],
            selectedNotableInvestments: [],
            selectedIndustry: "",
            selectedNotableInvestment: "",
            dataString: "",
            menus: [
                { menu: "industry-options-menu", button: "industry-options" },
                { menu: "round-options-menu", button: "round-options" },
                { menu: "notable-investment-options-menu", button: "notable-investment-options" },
            ],
            showClasses: ["transform", "opacity-100", "scale-100"],
            hideClasses: ["opacity-0", "scale-95", "pointer-events-none"],
        };
    },
    methods: {
        getValues() {
            const first_name = document.getElementById("first_name").value;
            const last_name = document.getElementById("last_name").value;
            const firm_name = document.getElementById("firm_name").value;
            const position = document.getElementById("position").value;
            const about = document.getElementById("about").value;
            const website = document.getElementById("website").value;
            const linkedin = document.getElementById("linkedin").value;
            const twitter = document.getElementById("twitter").value;
            const email = document.getElementById("email").value;
            const phone_number = document.getElementById("phone_number").value;
            const n_investments = document.getElementById("n_investments").value;
            const n_exits = document.getElementById("n_exits").value;
            const min_investment = document.getElementById("min_investment").value;
            const max_investment = document.getElementById("max_investment").value;
            const location = document.getElementById("location").value;

            const selectedRounds = Array.from(document.querySelectorAll('input[name="selected_rounds"]:checked')).map(
                (input) => parseInt(input.value, 10),
            );
            const selectedIndustries = Array.from(
                document.querySelectorAll('input[name="selected_industries"]:checked'),
            ).map((input) => parseInt(input.value, 10));
            const selectedNotableInvestments = Array.from(
                document.querySelectorAll('input[name="selected_notable_investments"]:checked'),
            ).map((input) => parseInt(input.value, 10));

            const dataString = JSON.stringify({
                first_name: first_name,
                last_name: last_name,
                firm_name: firm_name,
                position: position,
                about: about,
                website: website,
                linkedin: linkedin,
                twitter: twitter,
                email: email,
                phone_number: phone_number,
                n_investments: n_investments,
                n_exits: n_exits,
                min_investment: min_investment,
                max_investment: max_investment,
                location: location,
                rounds: selectedRounds,
                industries: selectedIndustries,
                notable_investments: selectedNotableInvestments,
            });

            return dataString;
        },
        async updateInvestor() {
            const csrfToken = document.getElementById("csrf_token").value;

            const dataString = this.getValues();

            try {
                const response = await fetch("", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: dataString,
                });
                if (response.redirected) {
                    window.location.href = response.url;
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
        setupMenuToggle() {
            this.menus.forEach(({ menu, button }) => {
                const menuElement = document.getElementById(menu);
                const buttonElement = document.getElementById(button);

                if (!menuElement || !buttonElement) return;

                document.addEventListener("click", (event) => {
                    if (!menuElement.contains(event.target) && !buttonElement.contains(event.target)) {
                        menuElement.classList.remove(...this.showClasses);
                        menuElement.classList.add(...this.hideClasses);
                    }
                });

                buttonElement.onclick = () => {
                    if (menuElement.classList.contains(this.hideClasses[0])) {
                        menuElement.classList.add(...this.showClasses);
                        menuElement.classList.remove(...this.hideClasses);
                    } else {
                        menuElement.classList.remove(...this.showClasses);
                        menuElement.classList.add(...this.hideClasses);
                    }
                };
            });
        },
        async getIndustryList(searchInput) {
            let industry_list = this.$refs.industryListElement;

            for (let i = 0; i < industry_list.children.length; i++) {
                if (industry_list.children[i].textContent.toUpperCase().includes(searchInput.toUpperCase())) {
                    industry_list.children[i].classList.remove("hidden");
                } else {
                    industry_list.children[i].classList.add("hidden");
                }
            }
        },
        async getNotableInvestmentList(searchInput) {
            let notable_investment_list = this.$refs.notableInvestmentListElement;

            for (let i = 0; i < notable_investment_list.children.length; i++) {
                if (notable_investment_list.children[i].textContent.toUpperCase().includes(searchInput.toUpperCase())) {
                    notable_investment_list.children[i].classList.remove("hidden");
                } else {
                    notable_investment_list.children[i].classList.add("hidden");
                }
            }
        },
        createCompany() {
            const csrfToken = document.getElementById("csrf_token").value;

            const formData = new FormData();

            if (this.$refs.picture && this.$refs.picture.files[0]) {
                formData.append("picture", this.$refs.picture.files[0]);
            }

            formData.append("company_name", this.$refs.company_name.value);
            formData.append("number_of_employees", this.$refs.number_of_employees.value);
            formData.append("description", this.$refs.description.value);
            formData.append("country", this.$refs.country.value);

            formData.append("round", this.$refs.round.value);
            formData.append("industry", this.$refs.industry.value);

            formData.append("website", this.$refs.website.value);

            fetch("/settings/company/create", {
                method: "POST",
                headers: {
                    "X-CSRFToken": csrfToken,
                },
                body: formData,
            })
                .then((response) => {
                    if (response.redirected) {
                        window.location.href = response.url;
                    }
                })
                .catch((error) => {
                    console.error("Error:", error);
                });
        },
    },
    mounted() {
        this.setupMenuToggle();
    },
}).mount("#app");
