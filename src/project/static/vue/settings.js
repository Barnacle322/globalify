const DeleteCompanyComponent = defineComponent({
    template: "#delete-company-template",
    methods: {
        closeDeleteCompany() {
            this.$emit("close-delete-company");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeDeleteCompany();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeDeleteCompany();
            }
        },
        async deleteCompany(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/settings/company/${companyId}/delete`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close-delete-company");
                }
            } catch (error) {
                console.error("Error cancelling invitation:", error.message);
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

const CancelInvitationComponent = defineComponent({
    template: "#cancel-invitation-template",
    props: ["invitation"],
    delimiters: ["[[", "]]"],
    methods: {
        closeCancelInvitation() {
            this.$emit("close-cancel-invitation");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeCancelInvitation();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeCancelInvitation();
            }
        },
        async cancelInvitation(invitationId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/settings/companies/invitation/${invitationId}/cancel`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("Failed to cancel invitation");
                }
            } catch (error) {
                console.error("Error cancelling invitation:", error.message);
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

const ChangeRoleComponent = defineComponent({
    template: "#change-role-template",
    props: ["user"],
    emits: ["close-change-role"],
    delimiters: ["[[", "]]"],
    data() {
        return {
            roles: [],
        };
    },
    methods: {
        closeChangeRole() {
            this.$emit("close-change-role");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeChangeRole();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeChangeRole();
            }
        },
        async changeRole(userId, companyId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const role = this.$refs.roleChange.value;

                const response = await fetch(`/settings/company/member/${userId}/role`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({
                        role: role,
                        company_id: companyId,
                    }),
                });

                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close-change-role");
                }
            } catch (error) {
                console.error("Error changing role:", error.message);
            }
        },
        async removeMember(userId, companyId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch(`/settings/company/member/${userId}/remove`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({
                        company_id: companyId,
                    }),
                });

                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close-change-role");
                }
            } catch (error) {
                console.error("Error removing member:", error.message);
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
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeConfirmRestore();
            }
        },
        async fetchPointOriginData() {
            try {
                const response = await fetch("/settings/investor/point-origin");
                if (response.redirected) {
                    window.location.href = response.url;
                }
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
                return this.investor_point_origin.notable_investments.join(", ");
            }
            return "";
        },
        roundsTitles() {
            if (this.investor_point_origin && this.investor_point_origin.rounds) {
                return this.investor_point_origin.rounds.join(", ");
            }
            return "";
        },
        industriesTitles() {
            if (this.investor_point_origin && this.investor_point_origin.industries) {
                return this.investor_point_origin.industries.join(", ");
            }
            return "";
        },
    },
    mounted() {
        this.fetchPointOriginData();
        window.addEventListener("keydown", this.handleKeyDown);
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
    },
    beforeUnmount() {
        this.investor_point_origin = {};
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },
});

const InviteMemberComponent = defineComponent({
    template: "#invite-member-template",
    data() {
        return {
            selectedUser: null,
            userList: [],
            roles: [],
            debouncedGetUserList: null,
            selectedRole: "",
            invitationMessage: "",
        };
    },
    methods: {
        limitText() {
            if (this.invitationMessage.length > 200) {
                this.invitationMessage = this.invitationMessage.slice(0, 200);
            }
        },
        handleSubmit(event) {
            event.preventDefault();
            this.inviteMember(this.$refs.companyId.value);
        },
        closeInviteMember() {
            this.$emit("close-invite-member");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeInviteMember();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeInviteMember();
            }
        },
        async inviteMember(companyId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const email = this.selectedUser.email;
                const role = this.selectedRole;
                const invitationMessage = this.invitationMessage;

                const response = await fetch(`/settings/company/${companyId}/invitation/create`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({
                        email: email,
                        role: role,
                        invitation_message: invitationMessage,
                    }),
                });

                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close-invite-member");
                }
            } catch (error) {
                console.error("Error inviting member:", error.message);
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
        async getUserList(event) {
            const searchInput = event.target.value;
            if (searchInput.length > 0) {
                const response = await fetch(`/settings/users/search/${searchInput}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.users && data.users.length > 0) {
                        this.userList = data.users;
                    } else if (data.search_input) {
                        this.userList = [{ email: data.search_input }];
                    } else {
                        this.userList = [];
                    }
                }
            } else {
                this.userList = [];
            }
        },
        selectUser(user, event) {
            event.stopPropagation();
            this.userList = [];
            this.selectedUser = user;
        },
        clearUser() {
            event.stopPropagation();
            this.selectedUser = null;
        },
        async fetchRoles() {
            try {
                const response = await fetch("/settings/companies/roles");
                if (response.ok) {
                    const data = await response.json();
                    this.roles = data.roles;
                } else {
                    console.error("Failed to fetch roles");
                }
            } catch (error) {
                console.error("Error fetching roles:", error.message);
            }
        },
    },
    mounted() {
        this.debouncedGetUserList = this.debounce(this.getUserList, 500);
        this.fetchRoles();
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

const GeneralInfo = defineComponent({
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

const InvestmentInfo = defineComponent({
    template: "#investment-info-template",
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

        this.data = JSON.parse(localStorage.getItem("investmentInfo")) || this.data;
        this.debouncedFetchNotableInvestmentList = this.debounce(this.fetchNotableInvestmentList, 500);
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
            this.save();
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
            localStorage.setItem("investmentInfo", JSON.stringify(this.data));
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
                nInvestments: null,
                nExits: null,
                minInvestment: null,
                maxInvestment: null,
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

const ContactInfo = defineComponent({
    template: "#contact-info-template",
    mounted() {
        this.email = this.$refs.userEmail.value;
        this.data = JSON.parse(localStorage.getItem("contactInfo")) || this.data;
    },
    methods: {
        previousPage() {
            this.save();
            this.$emit("change-page", -1);
        },
        save() {
            this.validateLinks();
            this.validateExistingInvestorByEmail();
            if (
                !this.errors.linkedin &&
                !this.errors.twitter &&
                !this.errors.email &&
                !this.errors.website &&
                !this.errors.phoneNumber
            ) {
                localStorage.setItem("contactInfo", JSON.stringify(this.data));
            }
        },
        validateField(field, pattern, fieldName) {
            if (this.data[field].trim() === "") {
                this.errors[field] = null;
            } else if (!this.data[field].match(pattern)) {
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
        async validateExistingInvestorByEmail() {
            try {
                const response = await fetch(`/onboarding/check-investor/${this.email}`);
                const data = await response.json();
                if (data.investor_exists) {
                    this.errors.email = "This email is already associated with an investor";
                } else {
                    this.errors.email = null;
                }
            } catch (error) {
                console.log(error);
            }
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
                this.save();
                try {
                    const response = await fetch("/settings/investor/create", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": document.getElementById("csrf_token").value,
                        },
                        body: JSON.stringify({
                            ...JSON.parse(localStorage.getItem("generalInfo")),
                            ...JSON.parse(localStorage.getItem("investmentInfo")),
                            ...JSON.parse(localStorage.getItem("contactInfo")),
                        }),
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
    data() {
        return {
            data: {
                website: "",
                linkedin: "",
                twitter: "",
                email: "",
                phoneNumber: "",
            },
            errors: {
                linkedin: null,
                twitter: null,
                email: null,
                website: null,
                phoneNumber: null,
            },
        };
    },
});

createApp({
    emits: ["close-confirm-restore", "close-invite-member", "close-change-role"],
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        Bookmark,
        ConfirmRestoreComponent,
        InviteMemberComponent,
        ChangeRoleComponent,
        CancelInvitationComponent,
        DeleteCompanyComponent,
        CreateNotableInvestmentComponent,
        GeneralInfo,
        InvestmentInfo,
        ContactInfo,
        CreateInvestmentComponent,
        DeleteInvestmentComponent,
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
        changeRoleOpened(value) {
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
        openDropdown(companyId) {
            this.openedDropdownCompanyId = companyId;
            this.ignoreNextOutsideClick = true;
        },
        closeDropdown(event) {
            if (this.ignoreNextOutsideClick) {
                this.ignoreNextOutsideClick = false;
            } else if (event && !this.$el.contains(event.target)) {
                this.openedDropdownCompanyId = false;
            }
        },
        getValues() {
            const first_name = document.getElementById("first_name").value;
            const last_name = document.getElementById("last_name").value;
            const firm_name = document.getElementById("firm_name").value;
            const position = document.getElementById("position").value;
            const about = document.getElementById("about").value;
            const website = document.getElementById("website").value;
            const linkedin = document.getElementById("investor_linkedin").value;
            const twitter = document.getElementById("investor_twitter").value;
            const email = document.getElementById("investor_email").value;
            const phone_number = document.getElementById("phone_number").value;
            const n_investments = document.getElementById("n_investments").value;
            const n_exits = document.getElementById("n_exits").value;
            const min_investment = document.getElementById("min_investment").value;
            const max_investment = document.getElementById("max_investment").value;
            const location = document.getElementById("location").value;
            const is_public = document.getElementById("is_public").checked;

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
                is_public: is_public,
            });

            return dataString;
        },
        async updateInvestor() {
            const csrfToken = document.getElementById("csrf_token").value;
            const dataString = this.getValues();

            try {
                const response = await fetch("/settings/investor", {
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
        async acceptInvitation(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/settings/company/${companyId}/invitation/accept`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("Failed to accept invitation");
                }
            } catch (error) {
                console.error("Error accepting invitation:", error.message);
            }
        },
        async declineInvitation(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/settings/company/${companyId}/invitation/decline`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("Failed to decline invitation");
                }
            } catch (error) {
                console.error("Error declining invitation:", error.message);
            }
        },
        async searchMembers(event) {
            searchInput = event.target.value;
            let member_list = this.$refs.memberListElement;

            for (let i = 0; i < member_list.children.length; i++) {
                if (member_list.children[i].textContent.toUpperCase().includes(searchInput.toUpperCase())) {
                    member_list.children[i].classList.remove("hidden");
                } else {
                    member_list.children[i].classList.add("hidden");
                }
            }
        },
        async makePrimary(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/settings/company/${companyId}/set-primary`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("Failed to make primary");
                }
            } catch (error) {
                console.error("Error making primary:", error.message);
            }
        },
        async togglePublic(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/settings/company/${companyId}/toggle-public`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("Failed to make public");
                }
            } catch (error) {
                console.error("Error making public:", error.message);
            }
        },
        async fetchNotableInvestmentList(event) {
            const searchInput = event.target.value.trim();

            if (searchInput.length > 0) {
                const response = await fetch(`/admin/companies/search_notable_investments/${searchInput}`);
                if (response.ok) {
                    const data = await response.json();
                    this.notableInvestmentList = data.notable_investments;
                }
            } else {
                this.notableInvestmentList = [];
            }
        },
        selectNotableInvestment(notable_investment) {
            this.$refs.searchInput.value = notable_investment;
            this.notableInvestmentList = [];
        },
        debounce(func, wait) {
            let timeout;
            return function (...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        },
        async fetchNotableInvestmentListByInvestorId(searchInput, investorId) {
            searchInput = searchInput.trim();

            if (searchInput.length > 0) {
                const response = await fetch(
                    `/admin/investors/search_notable_investments/${searchInput}/${investorId}`,
                );
                if (response.ok) {
                    const data = await response.json();
                    this.notableInvestmentList = data.notable_investments;
                }
            } else {
                this.notableInvestmentList = [];
            }
        },
    },
    mounted() {
        this.debouncedFetchNotableInvestmentList = this.debounce(this.fetchNotableInvestmentList, 500);
        this.debouncedFetchNotableInvestmentListByInvestorId = this.debounce(
            this.fetchNotableInvestmentListByInvestorId,
            500,
        );
        this.setupMenuToggle();
        window.addEventListener("click", this.closeDropdown);
    },
    computed: {
        currentComponent() {
            switch (this.currentPage) {
                case 1:
                    return "general-info";
                case 2:
                    return "investment-info";
                case 3:
                    return "contact-info";
                default:
                    return null;
            }
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            confirmRestoreOpened: false,
            inviteMemberOpened: false,
            deleteCompanyOpened: false,
            openedDropdownCompanyId: null,
            ignoreNextOutsideClick: false,
            createNotableInvestmentOpened: false,
            createInvestmentOpened: false,
            deleteInvestmentOpened: false,
            csrfToken: "",
            selectedRounds: [],
            selectedIndustries: [],
            selectedNotableInvestments: [],
            members: [],
            notableInvestmentList: [],
            debouncedFetchNotableInvestmentList: null,
            debouncedFetchNotableInvestmentListByInvestorId: null,
            selectedIndustry: "",
            selectedNotableInvestment: "",
            selectedUser: null,
            selectedInvitationId: null,
            dataString: "",
            currentPage: parseInt(localStorage.getItem("currentPage")) || 1,
            enterClass: "slide-fade-in-left",
            leaveClass: "slide-fade-out-left",
            menus: [
                { menu: "industry-options-menu", button: "industry-options" },
                { menu: "round-options-menu", button: "round-options" },
                { menu: "notable-investment-options-menu", button: "notable-investment-options" },
            ],
            showClasses: ["transform", "opacity-100", "scale-100"],
            hideClasses: ["opacity-0", "scale-95", "pointer-events-none"],
        };
    },
}).mount("#app");
