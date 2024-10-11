const InvestorRegistrationComponent = defineComponent({
    template: "#investor-registration-template",
    methods: {
        async openRegistrationPage() {
            this.$emit("change-page", 1);
        },
    },
});

const ClaimInvestorComponent = defineComponent({
    template: "#claim-investor-template",
    data() {
        return {};
    },
    methods: {
        goToSimilarInvestors() {
            this.$emit("change-page", 1);
        },
        createNewInvestor() {
            this.$emit("change-page", 2);
        },
        goToPreviousPage() {
            this.$emit("change-page", -1);
            // localStorage.setItem("currentPage", 0);
            // window.location.href = "/onboarding";
        },
    },
});

const ZeroPageComponent = defineComponent({
    template: "#zero-step-registration-template",
    components: {
        FullInvestor,
    },
    data() {
        return {
            investors: null,
            selectedInvestorSlug: null,
            debouncedInvestors: null,
        };
    },
    methods: {
        async fetchExistingInvestors() {
            try {
                const response = await fetch("/check-investor");
                const data = await response.json();
                this.investors = data.existing_investors;
            } catch (error) {
                console.log(error);
            }
        },
        selectInvestorSlug(investorSlug) {
            this.selectedInvestorSlug = investorSlug;
        },
        goToPreviousPage() {
            this.$emit("change-page", -1);
        },
        debounce(func, wait) {
            let timeout;
            return function (...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        },
        async searchInvestors(event) {
            const searchInput = event.target.value;

            if (searchInput.length > 0) {
                try {
                    const response = await fetch(`/search/investors/${searchInput}`);
                    const data = await response.json();
                    this.investors = data.investors;
                } catch (error) {
                    console.log(error);
                }
            } else {
                this.fetchExistingInvestors();
            }
        },
    },
    mounted() {
        this.debouncedInvestors = this.debounce(this.searchInvestors, 500);
    },
    created() {
        this.fetchExistingInvestors();
    },
});

const GeneralInfoComponent = defineComponent({
    template: "#general-info-template",
    mounted() {
        this.data.firstName = this.$refs.userFirstName.value;
        this.data = JSON.parse(localStorage.getItem("generalInfo")) || this.data;
    },
    methods: {
        nextPage() {
            this.validateFirstName();
            if (!this.errors.firstName) {
                this.save();
                this.$emit("change-page", 1);
            }
        },
        previousPage() {
            this.$emit("change-page", -2);
        },
        validateFirstName() {
            if (this.data.firstName.trim() === "") {
                this.errors.firstName = "The first name field is required!";
            } else {
                this.errors.firstName = null;
            }
        },
        save() {
            localStorage.setItem("generalInfo", JSON.stringify(this.data));
        },
    },
    data() {
        return {
            data: {
                firstName: "",
                lastName: "",
                firmName: "",
                position: "",
                location: "",
                about: "",
            },
            errors: {
                firstName: null,
            },
        };
    },
});

const SecondPageComponent = defineComponent({
    template: "#second-step-registration-template",
    mounted() {
        const menus = [
            { menu: "industry-options-menu", button: "industry-options" },
            { menu: "round-options-menu", button: "round-options" },
            { menu: "notable-investment-options-menu", button: "notable-investment-options" },
        ];
        const showClasses = ["transform", "opacity-100", "scale-100"];
        const hideClasses = ["opacity-0", "scale-95", "pointer-events-none"];

        menus.forEach(({ menu, button }) => {
            const menuElement = document.getElementById(menu);
            const buttonElement = document.getElementById(button);

            if (!menuElement || !buttonElement) return;

            document.addEventListener("click", (event) => {
                if (!menuElement.contains(event.target) && !buttonElement.contains(event.target)) {
                    menuElement.classList.remove(...showClasses);
                    menuElement.classList.add(...hideClasses);
                }
            });

            buttonElement.onclick = () => {
                if (menuElement.classList.contains(hideClasses[0])) {
                    menuElement.classList.add(...showClasses);
                    menuElement.classList.remove(...hideClasses);
                } else {
                    menuElement.classList.remove(...showClasses);
                    menuElement.classList.add(...hideClasses);
                }
            };
        });

        this.data = JSON.parse(localStorage.getItem("secondStepData")) || this.data;
    },
    methods: {
        nextPage() {
            this.validateNumbers();
            if (
                !this.errors.nInvestments &&
                !this.errors.nExits &&
                !this.errors.minInvestment &&
                !this.errors.maxInvestment
            ) {
                this.save();
                this.$emit("change-page", 1);
            }
        },
        previousPage() {
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
        save() {
            if (
                !this.errors.nInvestments &&
                !this.errors.nExits &&
                !this.errors.minInvestment &&
                !this.errors.maxInvestment
            ) {
                localStorage.setItem("secondStepData", JSON.stringify(this.data));
            }
        },
        async searchIndustryList(event) {
            const searchInput = event.target.value.toUpperCase();
            const industryList = this.$refs.industryListElement.children;

            for (let i = 0; i < industryList.length; i++) {
                const item = industryList[i];
                const text = item.textContent.toUpperCase();
                item.classList.toggle("hidden", !text.includes(searchInput));
            }
        },
        debounce(func, wait) {
            let timeout;
            return function (...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        },
        async fetchNotableInvestmentList(event) {
            const searchInput = event.target.value.trim();

            if (searchInput.length > 0) {
                try {
                    const response = await fetch(`/onboarding/search_notable_investments/${searchInput}`);
                    if (response.ok) {
                        const data = await response.json();
                        this.data.notableInvestmentList =
                            data.notable_investments.length > 0 ? data.notable_investments : [];
                    } else {
                        console.log("Error fetching notable investments");
                    }
                } catch (error) {
                    console.log(error);
                }
            } else {
                this.data.notableInvestmentList = [...this.data.selectedNotableInvestments];
            }
        },
    },
    data() {
        return {
            data: {
                selectedRounds: [],
                selectedIndustries: [],
                selectedNotableInvestments: [],
                notableInvestmentList: [],
                nInvestments: 0,
                nExits: 0,
                minInvestment: 0,
                maxInvestment: 0,
            },
            errors: {
                nInvestments: null,
                nExits: null,
                minInvestment: null,
                maxInvestment: null,
            },
        };
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
        ClaimInvestorComponent,
        ZeroPageComponent,
        GeneralInfoComponent,
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
