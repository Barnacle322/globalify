const { data } = "autoprefixer";

const { defineComponent, createApp } = Vue;

const InvestorRegistrationComponent = defineComponent({
    template: "#investor-registration-template",
    methods: {
        openRegistrationPage() {
            this.$emit("change-page", 1);
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
            errors: {
                firstName: null,
            },
        };
    },
    methods: {
        openNextPage() {
            this.validateFirstName();
            if (!this.errors.firstName) {
                this.saveFirstStepData();
                this.$emit("change-page", 1);
            }
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
        validateFirstName() {
            if (this.firstName.trim() === "") {
                this.errors.firstName = "The first name field is required!";
            } else {
                this.errors.firstName = null;
            }
        },
    },
    mounted() {
        this.firstName = this.$refs.userFirstName.value;
        this.lastName = this.$refs.userLastName.value;

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
            nInvestments: 0,
            nExits: 0,
            minInvestment: 0,
            maxInvestment: 0,
            errors: {
                nInvestments: null,
                nExits: null,
                minInvestment: null,
                maxInvestment: null,
            },
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
        openNextPage() {
            this.validateNumbers();
            if (
                !this.errors.nInvestments &&
                !this.errors.nExits &&
                !this.errors.minInvestment &&
                !this.errors.maxInvestment
            ) {
                this.saveSecondStepData();
                this.$emit("change-page", 1);
            }
        },
        goToPreviousPage() {
            this.$emit("change-page", -1);
        },
        validateField(field, value) {
            const MAX_INVESTMENT_LIMIT = 100000001;

            if (value == "") {
                this.errors[field] = null;
            } else if (Number(value) < 0) {
                this.errors[field] = "The value cannot be negative";
            } else {
                this.errors[field] = null;
            }

            if (field === "minInvestment" || field === "maxInvestment") {
                const minInvestment = Number(this.minInvestment);
                const maxInvestment = Number(this.maxInvestment);

                if (minInvestment > maxInvestment) {
                    this.errors["minInvestment"] = "Min investment cannot be greater than max investment";
                    this.errors["maxInvestment"] = "Max investment cannot be less than min investment";
                } else {
                    if (this.errors["minInvestment"] === "Min investment cannot be greater than max investment") {
                        this.errors["minInvestment"] = null;
                    }
                    if (this.errors["maxInvestment"] === "Max investment cannot be less than min investment") {
                        this.errors["maxInvestment"] = null;
                    }
                }
                if (maxInvestment > MAX_INVESTMENT_LIMIT) {
                    this.errors["maxInvestment"] = `Max investment cannot exceed ${MAX_INVESTMENT_LIMIT}`;
                }
            }
        },
        validateNumbers() {
            this.validateField("nInvestments", this.nInvestments);
            this.validateField("nExits", this.nExits);
            this.validateField("minInvestment", this.minInvestment);
            this.validateField("maxInvestment", this.maxInvestment);
        },
        saveSecondStepData() {
            this.validateNumbers();
            if (
                !this.errors.nInvestments &&
                !this.errors.nExits &&
                !this.errors.minInvestment &&
                !this.errors.maxInvestment
            ) {
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
            }
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

            if (searchInput.length > 0) {
                try {
                    const response = await fetch(`/onboarding/search_notable_investments/${searchInput}`);
                    if (response.ok) {
                        const data = await response.json();
                        this.notableInvestmentList =
                            data.notable_investments.length > 0 ? data.notable_investments : [];
                    } else {
                        console.log("Error fetching notable investments");
                    }
                } catch (error) {
                    console.log(error);
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
            errors: {
                linkedin: null,
                twitter: null,
                email: null,
                website: null,
                phoneNumber: null,
            },
        };
    },
    methods: {
        goToPreviousPage() {
            this.$emit("change-page", -1);
        },
        saveThirdStepData() {
            this.validateLinks();
            if (
                !this.errors.linkedin &&
                !this.errors.twitter &&
                !this.errors.email &&
                !this.errors.website &&
                !this.errors.phoneNumber
            ) {
                const formData = {
                    website: this.website,
                    linkedin: this.linkedin,
                    twitter: this.twitter,
                    email: this.email,
                    phone_number: this.phoneNumber,
                };
                localStorage.setItem("thirdStepData", JSON.stringify(formData));
            }
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
        validateField(field, pattern, fieldName) {
            if (this[field].trim() === "") {
                this.errors[field] = null;
            } else if (!this[field].match(pattern)) {
                this.errors[field] = `Please enter a valid ${fieldName} field`;
            } else {
                this.errors[field] = null;
            }
        },
        validateLinks() {
            this.validateField("linkedin", /^(https?:\/\/)?(www\.)?linkedin\.com\/in\/[A-Za-z0-9_-]+\/?$/, "LinkedIn");
            this.validateField(
                "twitter",
                /^(https?:\/\/)?((www\.)?twitter\.com|(www\.)?x\.com)\/[A-Za-z0-9_]+\/?$/,
                "Twitter",
            );
            this.validateField("website", /^(https?:\/\/)?(www\.)?[\w.-]+\.[a-z]{2,}\/?[\w.-]*$/, "Website");
            this.validateField("email", /^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$/, "Email");
            this.validateField(
                "phoneNumber",
                /^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$/,
                "Phone number",
            );
        },
        async submitRegistrationData() {
            this.validateLinks();
            if (
                !this.errors.linkedin &&
                !this.errors.twitter &&
                !this.errors.email &&
                !this.errors.website &&
                !this.errors.phoneNumber
            ) {
                this.saveThirdStepData();
                const csrfToken = document.getElementById("csrf_token").value;
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
            }
        },
    },
    mounted() {
        this.email = this.$refs.userEmail.value;

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
            currentPage: parseInt(localStorage.getItem("currentPage")) || 1,
            enterClass: "slide-fade-in-left",
            leaveClass: "slide-fade-out-left",
        };
    },
    methods: {
        changePage(pageNumber) {
            if (pageNumber > 0) {
                this.enterClass = "slide-fade-in-left";
                this.leaveClass = "slide-fade-out-left";
            } else {
                this.enterClass = "slide-fade-in-right";
                this.leaveClass = "slide-fade-out-right";
            }

            this.currentPage = this.currentPage + pageNumber;
            localStorage.setItem("currentPage", this.currentPage);
        },
    },
}).mount("#app");
