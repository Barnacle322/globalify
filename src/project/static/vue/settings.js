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
                const response = await fetch(`/settings/company/${invitationId}/cancel/invitation`, {
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

                const response = await fetch(`/settings/company/${userId}/change-role`, {
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
                const response = await fetch(`/settings/company/${userId}/remove`, {
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
        this.debouncedGetUserList = this.debounce(this.getUserList, 700);
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
            email: "",
            userList: [],
            roles: [],
            debouncedGetUserList: null,
            selectedRole: "",
            invitationMessage: "",
        };
    },
    methods: {
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
                const email = this.$refs.searchInput.value;
                const role = this.selectedRole;
                const invitationMessage = this.invitationMessage;

                const response = await fetch(`/settings/company/invite/${companyId}`, {
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
                const response = await fetch(`/settings/search_users/${searchInput}`);
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
        selectUser(email, event) {
            event.stopPropagation();
            this.$refs.searchInput.value = email;
            this.userList = [];
        },
        async fetchRoles() {
            try {
                const response = await fetch("/settings/company/roles");
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
        this.debouncedGetUserList = this.debounce(this.getUserList, 300);
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
            members: [],
            selectedIndustry: "",
            selectedNotableInvestment: "",
            selectedUser: null,
            selectedInvitationId: null,
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
        async acceptInvitation(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/settings/company/${companyId}/accept/invitation`, {
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
                const response = await fetch(`/settings/company/${companyId}/decline/invitation`, {
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
    },
    mounted() {
        this.setupMenuToggle();
    },
}).mount("#app");
