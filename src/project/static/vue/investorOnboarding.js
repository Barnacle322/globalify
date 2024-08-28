const { data } = "autoprefixer";

const { defineComponent, createApp } = Vue;

const InvestorRegistrationComponent = defineComponent({
    template: "#investor-registration-template",
    methods: {
        openRegistrationPage() {
            this.$emit("change-page", 2);
        },
    },
});

const FirstPageComponent = defineComponent({
    template: "#first-step-registration-template",
    data() {
        return {
            firstName: "",
            lastName: "",
            firmName: "",
            position: "",
            location: "",
            about: "",
        };
    },
    methods: {
        openSecondPage() {
            this.saveFirstStepData();
            this.$emit("change-page", 3);
        },
        saveFirstStepData() {
            const formData = {
                first_name: this.firstName,
                last_name: this.lastName,
                firm_name: this.firmName,
                position: this.position,
                location: this.location,
                about: this.about,
            };
            localStorage.setItem("firstStepData", JSON.stringify(formData));
        },
        loadFirstStepData() {
            const savedData = JSON.parse(localStorage.getItem("firstStepData"));
            if (savedData) {
                this.firstName = savedData.first_name || "";
                this.lastName = savedData.last_name || "";
                this.firmName = savedData.firm_name || "";
                this.position = savedData.position || "";
                this.location = savedData.location || "";
                this.about = savedData.about || "";
            }
        },
    },
    mounted() {
        this.loadFirstStepData();
    },
});

const SecondPageComponent = defineComponent({
    template: "#second-step-registration-template",
    data() {
        return {
            selectedRounds: [],
            selectedIndustries: [],
            selectedNotableInvestments: [],
            notableInvestmentList: [],
            nInvestments: "",
            nExits: "",
            minInvestment: "",
            maxInvestment: "",
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
        openThirdPage() {
            this.saveSecondStepData();
            this.$emit("change-page", 4);
        },
        goToPreviousPage() {
            this.$emit("change-page", 2);
        },
        saveSecondStepData() {
            const formData = {
                selectedRounds: this.selectedRounds,
                selectedIndustries: this.selectedIndustries,
                selectedNotableInvestments: this.selectedNotableInvestments,
                n_investments: this.nInvestments,
                n_exits: this.nExits,
                min_investment: this.minInvestment,
                max_investment: this.maxInvestment,
            };
            localStorage.setItem("secondStepData", JSON.stringify(formData));
        },
        loadSecondStepData() {
            const savedData = JSON.parse(localStorage.getItem("secondStepData"));
            if (savedData) {
                this.selectedRounds = savedData.selectedRounds || [];
                this.selectedIndustries = savedData.selectedIndustries || [];
                this.selectedNotableInvestments = savedData.selectedNotableInvestments || [];
                this.n_investments = savedData.n_investments || "";
                this.n_exits = savedData.n_exits || "";
                this.min_investment = savedData.min_investment || "";
                this.max_investment = savedData.max_investment || "";
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
        async fetchNotableInvestmentList(event) {
            const searchInput = event.target.value.trim();

            console.log(searchInput);

            if (searchInput.length > 0) {
                const response = await fetch(`/admin/companies/search_notable_investments/${searchInput}`);
                const data = await response.json();
                console.log(data);
                if (response.ok) {
                    const data = await response.json();
                    console.log(data);
                    this.notableInvestmentList = data.notable_investments.length > 0 ? data.notable_investments : [];
                } else {
                    console.log("Error fetching notable investments");
                }
            } else {
                this.notableInvestmentList = [...this.selectedNotableInvestments];
            }
        },
    },
    mounted() {
        this.setupMenuToggle();
        this.loadSecondStepData();
    },
});

const ThirdPageComponent = defineComponent({
    template: "#third-step-registration-template",
    data() {
        return {
            website: "",
            linkedin: "",
            twitter: "",
            email: "",
            phoneNumber: "",
        };
    },
    methods: {
        goToPreviousPage() {
            this.$emit("change-page", 3);
        },
        saveThirdStepData() {
            const formData = {
                website: this.website,
                linkedin: this.linkedin,
                twitter: this.twitter,
                email: this.email,
                phone_number: this.phoneNumber,
            };
            localStorage.setItem("thirdStepData", JSON.stringify(formData));
        },
        loadThirdStepData() {
            const savedData = JSON.parse(localStorage.getItem("thirdStepData"));
            if (savedData) {
                this.website = savedData.website || "";
                this.linkedin = savedData.linkedin || "";
                this.twitter = savedData.twitter || "";
                this.email = savedData.email || "";
                this.phone_number = savedData.phone_number || "";
            }
        },
        async submitRegistrationData() {
            const csrfToken = document.getElementById("csrf_token").value;
            this.saveThirdStepData();
            const firstStepData = JSON.parse(localStorage.getItem("firstStepData"));
            const secondStepData = JSON.parse(localStorage.getItem("secondStepData"));
            const thirdStepData = JSON.parse(localStorage.getItem("thirdStepData"));

            const formData = {
                ...firstStepData,
                ...secondStepData,
                ...thirdStepData,
            };

            try {
                const response = await fetch("/onboarding/investor", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify(formData),
                });
                if (response.redirected) {
                    window.location.href = response.url;
                }
            } catch (error) {
                console.log("Error submitting registration data", error);
            }
        },
    },
    mounted() {
        this.loadThirdStepData();
    },
});

createApp({
    components: {
        InvestorRegistrationComponent,
        FirstPageComponent,
        SecondPageComponent,
        ThirdPageComponent,
    },

    data() {
        return {
            currentPage: 1,
        };
    },
    methods: {
        changePage(pageNumber) {
            this.currentPage = pageNumber;
        },
    },
    mounted() {
        console.log("Investor onboarding component mounted");
        console.log(this.secondPageOpened);
    },
    created() {
        console.log("Investor onboarding component created");
    },
    watch() {
        console.log("Investor onboarding component watch");
    },
}).mount("#app");
