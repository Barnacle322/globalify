const DeleteInvestmentComponent = defineComponent({
    template: "#delete-investment-template",
    props: ["id"],
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
        async deleteInvestment(investmentId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investment/${investmentId}/delete`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("An error occurred while deleting the investment.");
                }
            } catch (error) {
                console.error("Error cancelling invitation:", error.message);
            }
        },
        closeDeleteInvestment() {
            this.$emit("close-delete-investment");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeDeleteInvestment();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeDeleteInvestment();
            }
        },
    },
});

const UpdateInvestmentComponent = defineComponent({
    template: "#update-investment-template",
    props: ["id", "companyid"],
    components: {
        DeleteInvestmentComponent,
    },
    async created() {
        await this.fetchInvestment(this.id);
        await this.fetchFundingRounds();
        this.selectedInvestor = this.investment.investor;
        this.selectedInvestmentFirm = this.investment.investment_firm;
        this.selectedFundingRound = this.investment.funding_round_id;

        if (this.investment.custom_name) {
            this.customName = this.investment.custom_name;
            this.selectedCustomName = true;
        }
    },
    mounted() {
        this.debouncedInvestorList = this.debounce(this.getInvestorList, 500);
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
        async updateInvestment(id, isAdmin) {
            const { value: csrf_token } = document.getElementById("csrf_token");
            const { value: amount } = document.getElementById("amount");
            const { value: date } = document.getElementById("date");

            const payload = {
                custom_name: this.customName,
                funding_round_id: this.selectedFundingRound,
                amount,
                date,
                created_by_admin: isAdmin,
                investor_id: this.selectedInvestor?.id || null,
                investment_firm_id: this.selectedInvestmentFirm?.id || null,
            };

            try {
                const response = await fetch(`/investment/${id}/update`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                    body: JSON.stringify(payload),
                });

                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("Failed to update investment:", response.statusText);
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
        async fetchInvestment(investmentId) {
            try {
                const response = await fetch(`/investment/${investmentId}`);
                if (response.ok) {
                    const data = await response.json();
                    this.investment = data.investment;
                }
            } catch (error) {
                console.error("Error fetching investment:", error);
            }
        },
        async fetchFundingRounds() {
            try {
                const response = await fetch(`/settings/company/${this.companyid}/funding-rounds`);
                if (response.ok) {
                    data = await response.json();
                    this.fundingRounds = data.funding_rounds;
                    this.fundingRounds.forEach((fundingRound) => {
                        fundingRound.announced_date = new Date(
                            fundingRound.announced_date.split("T")[0],
                        ).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                        });
                    });
                }
            } catch (error) {
                console.error("Error fetching funding rounds:", error);
            }
        },
        async getInvestorList(event) {
            const searchInput = event.target.value;
            if (searchInput.length > 0) {
                const response = await fetch(`/search/${searchInput}`);
                if (response.ok) {
                    const data = await response.json();
                    this.investors = data.results || [];
                    this.searchPerformed = true;
                } else {
                    console.error("Failed to fetch search results");
                }
            } else {
                this.investors = [];
                this.searchPerformed = false;
            }
        },
        selectAsCustomName() {
            this.selectedCustomName = true;
            this.customName = this.searchQuery;
            this.searchPerformed = false;
            this.selectedInvestor = null;
        },
        selectInvestor(investor) {
            this.investors = [];
            if (investor.type === "investor") {
                this.selectedInvestor = investor;
                this.selectedInvestmentFirm = null;
            } else if (investor.type === "investment_firm") {
                this.selectedInvestmentFirm = investor;
                this.selectedInvestor = null;
            }
            this.customName = "";
        },
        clearInput() {
            this.searchQuery = "";
            this.customName = "";
            this.selectedInvestor = null;
            this.selectedInvestmentFirm = null;
            this.selectedCustomName = false;
            this.showInvestorList = false;
        },
        debounce(func, wait) {
            let timeout;
            return function (...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        },
        closeUpdateInvestmentModal() {
            this.$emit("close");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.closeUpdateInvestmentModal();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.closeUpdateInvestmentModal();
            }
        },
        hideInvestorList() {
            this.showInvestorList = false;
        },
    },
    data() {
        return {
            investors: [],
            fundingRounds: [],
            investment: {},
            debouncedInvestorList: null,
            selectedInvestor: null,
            selectedInvestmentFirm: null,
            selectedFundingRound: null,
            selectedCustomName: false,
            searchPerformed: false,
            showInvestorList: false,
            deleteInvestmentOpened: false,
            customName: "",
            searchQuery: "",
        };
    },
});

const CreateInvestmentComponent = defineComponent({
    template: "#create-investment-template",
    props: ["type", "companyid"],
    async created() {
        this.fetchFundingRounds();
    },
    mounted() {
        this.debouncedInvestorList = this.debounce(this.getInvestorList, 500);
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
        async createInvestment(isAdmin) {
            const csrf_token = document.getElementById("csrf_token").value;
            const amount = document.getElementById("amount").value;
            const date = document.getElementById("announced_date").value;
            const announced_date = document.getElementById("announced_date").value;
            const payload = {
                custom_name: this.customName,
                funding_round_id: this.selectedFundingRound,
                amount: amount,
                date: date,
                created_by_admin: isAdmin,
                date: announced_date,
                investor_id: this.selectedInvestor?.id || null,
                investment_firm_id: this.selectedInvestmentFirm?.id || null,
            };

            try {
                const response = await fetch("/investment/create", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                    body: JSON.stringify(payload),
                });
                if (response.ok) {
                    window.location.reload();
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
        async fetchFundingRounds() {
            try {
                const response = await fetch(`/settings/company/${this.companyid}/funding-rounds`);
                if (response.ok) {
                    data = await response.json();
                    this.fundingRounds = data.funding_rounds;
                    this.fundingRounds.forEach((fundingRound) => {
                        fundingRound.announced_date = new Date(
                            fundingRound.announced_date.split("T")[0],
                        ).toLocaleDateString("en-US", {
                            year: "numeric",
                            month: "short",
                            day: "numeric",
                        });
                    });
                }
            } catch (error) {
                console.error("Error fetching funding rounds:", error);
            }
        },
        async getInvestorList(event) {
            const searchInput = event.target.value;
            if (searchInput.length > 0) {
                const response = await fetch(`/search/${searchInput}`);
                if (response.ok) {
                    const data = await response.json();
                    this.investors = data.results || [];
                    this.searchPerformed = true;
                } else {
                    console.error("Failed to fetch search results");
                }
            } else {
                this.investors = [];
                this.searchPerformed = false;
            }
        },
        selectAsCustomName() {
            this.selectedCustomName = true;
            this.customName = this.searchQuery;
            this.searchPerformed = false;
            this.selectedInvestor = null;
        },
        selectInvestor(investor) {
            this.investors = [];
            if (investor.type === "investor") {
                this.selectedInvestor = investor;
                this.selectedInvestmentFirm = null;
            } else if (investor.type === "investment_firm") {
                this.selectedInvestmentFirm = investor;
                this.selectedInvestor = null;
            }
            this.customName = "";
        },
        clearInput() {
            this.searchQuery = "";
            this.customName = "";
            this.selectedInvestor = null;
            this.selectedInvestmentFirm = null;
            this.selectedCustomName = false;
            this.showInvestorList = false;
        },
        debounce(func, wait) {
            let timeout;
            return function (...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        },
        close() {
            this.$emit("close");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.close();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.close();
            }
        },
        hideInvestorList() {
            this.showInvestorList = false;
        },
    },
    data() {
        return {
            investors: [],
            fundingRounds: [],
            debouncedInvestorList: null,
            selectedInvestor: null,
            selectedInvestmentFirm: null,
            selectedFundingRound: null,
            selectedCustomName: false,
            searchPerformed: false,
            showInvestorList: false,
            customName: "",
            searchQuery: "",
        };
    },
});

const CreateFundingRoundComponent = defineComponent({
    template: "#create-funding-round-template",
    async created() {
        this.fetchRounds();
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
        async createFundingRound(companyId) {
            const csrf_token = document.getElementById("csrf_token").value;
            const announced_date = document.getElementById("announced_date").value;

            const dataString = JSON.stringify({
                company_id: companyId,
                round_id: this.selectedRound,
                announced_date: announced_date,
            });

            try {
                const response = await fetch("/investment/funding-round/create", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                    body: dataString,
                });
                if (response.ok) {
                    window.location.reload();
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
        async fetchRounds() {
            try {
                const response = await fetch("/settings/rounds");
                if (response.ok) {
                    data = await response.json();
                    this.rounds = data.rounds;
                }
            } catch (error) {
                console.error("Error fetching rounds:", error);
            }
        },
        close() {
            this.$emit("close");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.close();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.close();
            }
        },
    },

    data() {
        return {
            rounds: [],
            selectedCompany: null,
            selectedRound: null,
        };
    },
});

const UpdateFundingRoundComponent = defineComponent({
    template: "#update-funding-round-template",
    props: ["id"],
    async created() {
        this.fetchRounds();
        await this.fetchFundingRound(this.id);
        this.selectedRound = this.fundingRound.round_id;
        this.selectedCompany = this.fundingRound.company_id;
        this.selectedAnnouncedDate = this.fundingRound.announced_date;
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
        async updateFundingRound(id) {
            const csrf_token = document.getElementById("csrf_token").value;
            const announced_date = document.getElementById("announced_date").value;

            const dataString = JSON.stringify({
                company_id: this.selectedCompany,
                round_id: this.selectedRound,
                announced_date: announced_date,
            });

            try {
                const response = await fetch(`/investment/funding-round/${id}/update`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                    body: dataString,
                });
                if (response.ok) {
                    window.location.reload();
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
        async fetchRounds() {
            try {
                const response = await fetch("/settings/rounds");
                if (response.ok) {
                    data = await response.json();
                    this.rounds = data.rounds;
                }
            } catch (error) {
                console.error("Error fetching rounds:", error);
            }
        },
        async fetchFundingRound(id) {
            try {
                const response = await fetch(`/investment/funding-round/${id}`);
                if (response.ok) {
                    const data = await response.json();
                    this.fundingRound = data.funding_round;
                }
            } catch (error) {
                console.error("Error fetching funding round:", error);
            }
        },
        close() {
            this.$emit("close-update-funding-round");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.close();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.close();
            }
        },
    },

    data() {
        return {
            rounds: [],
            selectedCompany: null,
            selectedRound: null,
            selectedAnnouncedDate: null,
            fundingRoundId: null,
            fundingRound: {},
        };
    },
});

const DeleteFundingRoundComponent = defineComponent({
    template: "#delete-funding-round-template",
    props: ["funding-round-id"],
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
        async deleteFundingRound(fundingRoundId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investment/funding-round/${fundingRoundId}/delete`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    window.location.reload();
                } else {
                    console.error("An error occurred while deleting the investment.");
                }
            } catch (error) {
                console.error("Error cancelling invitation:", error.message);
            }
        },
        close() {
            this.$emit("close");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.close();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.close();
            }
        },
    },
});

const AddMemberComponent = defineComponent({
    template: "#add-member-template",
    emits: ["close"],
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
    methods: {
        debounce(func, wait) {
            let timeout;
            return function (...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        },
        close() {
            this.$emit("close");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.close();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.close();
            }
        },
        limitPositionText() {
            if (this.data.position.length > 200) {
                this.data.position = this.data.position.slice(0, 200);
            }
        },
        selectUser(user, event) {
            event.stopPropagation();
            this.userList = [];
            this.selectedUser = user;
        },
        clearUser() {
            this.selectedUser = null;
        },
        async addMember(companyId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;

                const response = await fetch(`/admin/companies/${companyId}/members/add`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ ...this.data, user_id: this.selectedUser.id }),
                });

                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close");
                }
            } catch (error) {
                console.error("Error inviting member:", error.message);
            }
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
    data() {
        return {
            selectedUser: null,
            userList: [],
            roles: [],
            debouncedGetUserList: null,
            data: {
                role: "",
                position: "",
                is_primary: false,
                is_public: false,
            },
        };
    },
});

const EditMemberComponent = defineComponent({
    template: "#edit-member-template",
    props: ["user"],
    emits: ["close"],
    delimiters: ["[[", "]]"],
    mounted() {
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
    methods: {
        close() {
            this.$emit("close");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.close();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.close();
            }
        },
        async editMember(userId, companyId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch(`/admin/companies/${companyId}/members`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ ...this.data, user_id: userId }),
                });

                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close");
                }
            } catch (error) {
                console.error("Error changing role:", error.message);
            }
        },
        async removeMember(userId, companyId) {
            try {
                const response = await fetch(`/admin/companies/${companyId}/members/${userId}/remove`, {
                    headers: {
                        "Content-Type": "application/json",
                    },
                });

                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close");
                }
            } catch (error) {
                console.error("Error removing member:", error.message);
            }
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
    data() {
        return {
            roles: [],
            data: {
                role: this.user.role.toUpperCase(),
                position: this.user.position,
                is_primary: Boolean(this.user.is_primary),
                is_public: Boolean(this.user.is_public),
            },
        };
    },
});

const AddCompanyComponent = defineComponent({
    template: "#add-company-template",
    emits: ["close"],
    delimiters: ["[[", "]]"],
    mounted() {
        this.debouncedGetCompanyList = this.debounce(this.getCompanyList, 500);
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
    methods: {
        debounce(func, wait) {
            let timeout;
            return function (...args) {
                const context = this;
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(context, args), wait);
            };
        },
        limitPositionText() {
            if (this.data.position.length > 200) {
                this.data.position = this.data.position.slice(0, 200);
            }
        },
        close() {
            this.$emit("close");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.close();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.close();
            }
        },
        selectCompany(company, event) {
            event.stopPropagation();
            this.companyList = [];
            this.selectedCompany = company;
        },
        clearUser() {
            this.companyList = null;
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
        async addCompany(userId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;

                const response = await fetch(`/admin/users/${userId}/companies/add`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ ...this.data, company_id: this.selectedCompany.id }),
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
        async getCompanyList(event) {
            const searchInput = event.target.value;
            if (searchInput.length > 0) {
                const response = await fetch(`/settings/companies/search/${searchInput}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.companies && data.companies.length > 0) {
                        this.companyList = data.companies;
                    } else if (data.search_input) {
                        this.companyList = [{ email: data.search_input }];
                    } else {
                        this.companyList = [];
                    }
                }
            } else {
                this.companyList = [];
            }
        },
    },
    data() {
        return {
            selectedCompany: null,
            companyList: [],
            roles: [],
            debouncedGetCompanyList: null,
            data: {
                role: "",
                position: "",
                is_public: false,
                is_primary: false,
            },
        };
    },
});

const EditCompanyMemberComponent = defineComponent({
    template: "#edit-company-member-template",
    props: ["user_company"],
    emits: ["close"],
    delimiters: ["[[", "]]"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        this.fetchRoles();
        setTimeout(() => {
            document.addEventListener("click", this.handleOutsideClick);
        }, 0);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        document.removeEventListener("click", this.handleOutsideClick);
    },

    methods: {
        close() {
            this.$emit("close");
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.close();
            }
        },
        handleOutsideClick(event) {
            if (!this.$el.contains(event.target)) {
                this.close();
            }
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
        async editMember(userId, companyId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;

                const response = await fetch(`/admin/users/${userId}/companies`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                    body: JSON.stringify({ ...this.data, company_id: companyId }),
                });

                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close");
                }
            } catch (error) {
                console.error("Error changing role:", error.message);
            }
        },
        async removeMember(userId, companyId) {
            try {
                const response = await fetch(`/admin/users/${userId}/companies/${companyId}/remove`, {
                    headers: {
                        "Content-Type": "application/json",
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (response.ok) {
                    this.$emit("close");
                }
            } catch (error) {
                console.error("Error removing member:", error.message);
            }
        },
    },
    data() {
        return {
            roles: [],
            data: {
                role: this.user_company.user_role.toUpperCase(),
                position: this.user_company.user_position,
                is_primary: Boolean(this.user_company.is_primary),
                is_public: Boolean(this.user_company.is_public),
            },
        };
    },
});

createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        Bookmark,
        CreateNotableInvestmentComponent,
        CreateInvestmentComponent,
        DeleteInvestmentComponent,
        UpdateInvestmentComponent,
        CreateFundingRoundComponent,
        UpdateFundingRoundComponent,
        DeleteFundingRoundComponent,
        EditMemberComponent,
        EditCompanyMemberComponent,
        AddMemberComponent,
        AddCompanyComponent,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    created() {
        this.asideMinified = localStorage.getItem("asideMinified") === "true";
        this.debouncedInvestments = this.debounce(this.fetchNotableInvestments, 500);
        this.debouncedInvestorInvestments = this.debounce(this.fetchNotableInvestmentsByInvestorId, 500);
        this.debouncedInvestmentFirmInvestments = this.debounce(this.fetchNotableInvestmentsByInvestmentFirmId, 500);
    },
    methods: {
        openUpdateInvestment(investment) {
            this.investment = investment;

            console.log(this.investment);
            this.updateInvestmentOpened = true;
        },
        async submitInvestmentData() {
            const csrfToken = document.getElementById("csrf_token").value;

            const investor_id = document.getElementById("investor").value;
            const investment_firm_id = document.getElementById("investment_firm").value;
            const custom_name = document.getElementById("custom_name").value;
            const funding_round_id = document.getElementById("funding_round").value;
            const amount = document.getElementById("amount").value;
            const announced_date = document.getElementById("announced_date").value;
            const createdByAdminElement = document.getElementById("created_by_admin");
            const created_by_admin = createdByAdminElement ? createdByAdminElement.checked : false;
            const isVerifiedElement = document.getElementById("is_verified");
            const is_verified = isVerifiedElement ? isVerifiedElement.checked : false;

            const dataString = JSON.stringify({
                investor_id: investor_id,
                investment_firm_id: investment_firm_id,
                custom_name: custom_name,
                funding_round_id: funding_round_id,
                amount: amount,
                date: announced_date,
                created_by_admin: created_by_admin,
                is_verified: is_verified,
            });

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
        async submitFundingRoundData() {
            const csrfToken = document.getElementById("csrf_token").value;

            const company_id = document.getElementById("company").value;
            const custom_company_name = document.getElementById("custom_company_name").value;
            const round_id = document.getElementById("round").value;
            const announced_date = document.getElementById("announced_date").value;

            const dataString = JSON.stringify({
                company_id: company_id,
                custom_company_name: custom_company_name,
                round_id: round_id,
                announced_date: announced_date,
            });

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
        async submitInvestorData() {
            const csrfToken = document.getElementById("csrf_token").value;

            const first_name = document.getElementById("first_name").value;
            const last_name = document.getElementById("last_name").value;
            const slug = document.getElementById("slug").value;
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
            const user_email = document.getElementById("searchInput").value;

            const selectedRounds = Array.from(document.querySelectorAll('input[name="selected_rounds"]:checked')).map(
                (input) => parseInt(input.value, 10),
            );
            const selectedIndustries = Array.from(
                document.querySelectorAll('input[name="selected_industries"]:checked'),
            ).map((input) => parseInt(input.value, 10));
            const selectedNotableInvestments = Array.from(
                document.querySelectorAll('input[name="selected_notable_investments"]:checked'),
            ).map((input) => parseInt(input.value, 10));
            const is_public = document.getElementById("is_public");
            const is_approved = document.getElementById("is_approved");

            let data = {
                first_name: first_name,
                last_name: last_name,
                slug: slug,
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
                user_email: user_email,
                rounds: selectedRounds,
                industries: selectedIndustries,
                notable_investments: selectedNotableInvestments,
            };

            if (is_public) {
                data.is_public = is_public.checked;
            }
            if (is_approved) {
                data.is_approved = is_approved.checked;
            }

            let dataString = JSON.stringify(data);

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
        async submitExpertData() {
            const csrfToken = document.getElementById("csrf_token").value;
            const first_name = document.getElementById("first_name").value;
            const last_name = document.getElementById("last_name").value;
            const slug = document.getElementById("slug").value;
            const firm_name = document.getElementById("firm_name").value;
            const position = document.getElementById("position").value;
            const location = document.getElementById("location").value;
            const bio = document.getElementById("bio").value;
            const price = document.getElementById("price").value;
            const description = document.getElementById("description").value;
            const linkedin = document.getElementById("linkedin").value;
            const twitter = document.getElementById("twitter").value;
            const email = document.getElementById("email").value;
            const phone_number = document.getElementById("phone_number").value;
            const user_email = document.getElementById("searchInput").value;
            let data = {
                first_name: first_name,
                last_name: last_name,
                slug: slug,
                firm_name: firm_name,
                position: position,
                location: location,
                bio: bio,
                price: price,
                description: description,
                linkedin: linkedin,
                twitter: twitter,
                email: email,
                phone_number: phone_number,
                user_email: user_email,
            };

            let dataString = JSON.stringify(data);

            try {
                const response = await fetch("/admin/experts/create", {
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
        async deleteInvestor(id) {
            const csrfToken = document.getElementById("csrf_token").value;

            if (!confirm("Are you sure you want to delete this investor?")) {
                return;
            }

            const response = await fetch(`/admin/investors/${id}/delete`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
            });
            if (response.redirected) {
                window.location.href = response.url;
            }
        },
        async approveInvestor(investorId) {
            const csrfToken = document.getElementById("csrf_token").value;

            try {
                const response = await fetch(`/admin/investors/${investorId}/approve`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
        async undoInvestorData(investorId) {
            const csrfToken = document.getElementById("csrf_token").value;

            try {
                const response = await fetch(`/admin/investors/${investorId}/undo`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                }
            } catch (error) {
                console.error("Error:", error);
            }
        },
        async restoreOriginData(investorId) {
            try {
                const response = await fetch(`/admin/investors/${investorId}/restore`, {
                    method: "GET",
                });
                if (response.redirected) {
                    window.location.href = response.url;
                }
            } catch (error) {
                console.error("There has been a problem with your fetch operation:", error);
            }
        },
        async submitInvestmentFirmData() {
            const csrfToken = document.getElementById("csrf_token").value;

            const name = document.getElementById("name").value;
            const slug = document.getElementById("slug").value;
            const about = document.getElementById("about").value;
            const website = document.getElementById("website").value;
            const email = document.getElementById("email").value;
            const phone_number = document.getElementById("phone_number").value;
            const n_investments = document.getElementById("n_investments").value;
            const n_exits = document.getElementById("n_exits").value;
            const n_employees = document.getElementById("n_employees").value;
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
            const is_public = document.getElementById("is_public");

            let data = {
                name: name,
                slug: slug,
                about: about,
                website: website,
                email: email,
                phone_number: phone_number,
                n_investments: n_investments,
                n_exits: n_exits,
                n_employees: n_employees,
                min_investment: min_investment,
                max_investment: max_investment,
                location: location,
                rounds: selectedRounds,
                industries: selectedIndustries,
                notable_investments: selectedNotableInvestments,
            };

            if (is_public) {
                data.is_public = is_public.checked;
            }

            let dataString = JSON.stringify(data);

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
        async deleteInvestmentFirm(id) {
            const csrfToken = document.getElementById("csrf_token").value;

            if (!confirm("Are you sure you want to delete this investment firm?")) {
                return;
            }

            const response = await fetch(`/admin/investment-firms/${id}/delete`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
            });
            if (response.redirected) {
                window.location.href = response.url;
            }
        },
        async submitCompanyData() {
            const csrfToken = document.getElementById("csrf_token").value;

            const name = document.getElementById("name").value;
            const slug = document.getElementById("slug").value;
            const description = document.getElementById("description").value;
            const country = document.getElementById("country").value;
            const preferred_round = document.getElementById("round").value;
            const industry = document.getElementById("industry").value;
            const number_of_employees = document.getElementById("number_of_employees").value;
            const website = document.getElementById("website").value;
            const linkedin = document.getElementById("linkedin").value;
            const twitter = document.getElementById("twitter").value;
            const instagram = document.getElementById("instagram").value;
            const isPublicElement = document.getElementById("is_public");
            const is_public = isPublicElement ? isPublicElement.checked : true;

            const selectedNotableInvestments = Array.from(
                document.querySelectorAll('input[name="selected_notable_investments"]:checked'),
            ).map((input) => parseInt(input.value, 10));

            const dataString = JSON.stringify({
                name: name,
                slug: slug,
                description: description,
                country: country,
                preferred_round: preferred_round,
                industry: industry,
                number_of_employees: number_of_employees,
                website: website,
                linkedin: linkedin,
                twitter: twitter,
                instagram: instagram,
                is_public: is_public,
                notable_investment: selectedNotableInvestments,
            });

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
        async deleteCompany(id) {
            const csrfToken = document.getElementById("csrf_token").value;

            if (!confirm("Are you sure you want to delete this company?")) {
                return;
            }

            const response = await fetch(`/admin/companies/${id}/delete`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
            });
            if (response.redirected) {
                window.location.href = response.url;
            }
        },
        async submitUserData() {
            const csrfToken = document.getElementById("csrf_token").value;

            const firstName = document.getElementById("first_name").value;
            const lastName = document.getElementById("last_name").value;
            const email = document.getElementById("email").value;
            const isVerifiedElement = document.getElementById("is_verified");
            const is_verified = isVerifiedElement ? isVerifiedElement.checked : false;
            const isAdminElement = document.getElementById("is_admin");
            const is_admin = isAdminElement ? isAdminElement.checked : false;

            const username = document.getElementById("username").value;
            const bio = document.getElementById("bio").value;
            const instagram = document.getElementById("instagram").value;
            const linkedin = document.getElementById("linkedin").value;
            const twitter = document.getElementById("twitter").value;
            const isCompleteElement = document.getElementById("is_complete");
            const is_complete = isCompleteElement ? isCompleteElement.checked : false;
            const refuseAllInvitationsElement = document.getElementById("refuse_all_invitations");
            const refuse_all_invitations = refuseAllInvitationsElement ? refuseAllInvitationsElement.checked : false;
            const emailPublicElement = document.getElementById("email_public");
            const email_public = emailPublicElement ? emailPublicElement.checked : false;
            const instagramPublicElement = document.getElementById("instagram_public");
            const instagram_public = instagramPublicElement ? instagramPublicElement.checked : false;
            const linkedinPublicElement = document.getElementById("linkedin_public");
            const linkedin_public = linkedinPublicElement ? linkedinPublicElement.checked : false;
            const twitterPublicElement = document.getElementById("twitter_public");
            const twitter_public = twitterPublicElement ? twitterPublicElement.checked : false;

            const customerId = document.getElementById("customer_id").value;
            const subscriptionId = document.getElementById("subscription_id").value;
            const tier = document.getElementById("tier").value;
            const isActiveElement = document.getElementById("is_active");
            const is_active = isActiveElement ? isActiveElement.checked : false;
            const created = document.getElementById("created").value;
            const expires_at = document.getElementById("expires_at").value;

            const dataString = JSON.stringify({
                email: email,
                first_name: firstName,
                last_name: lastName,
                is_verified: is_verified,
                is_admin: is_admin,

                username: username,
                bio: bio,
                instagram: instagram,
                linkedin: linkedin,
                twitter: twitter,
                is_complete: is_complete,
                refuse_all_invitations: refuse_all_invitations,
                email_public: email_public,
                instagram_public: instagram_public,
                linkedin_public: linkedin_public,
                twitter_public: twitter_public,

                customer_id: customerId,
                subscription_id: subscriptionId,
                tier: tier,
                is_active: is_active,
                created: created,
                expires_at: expires_at,
            });
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
        async deleteUser(id) {
            const csrfToken = document.getElementById("csrf_token").value;

            if (!confirm("Are you sure you want to delete this user?")) {
                return;
            }

            const response = await fetch(`/admin/users/${id}/delete`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
            });
            if (response.redirected) {
                window.location.href = response.url;
            }
        },
        selectUser(email) {
            this.$refs.searchInput.value = email;
            this.userList = [];
        },
        selectNotableInvestment(notable_investment) {
            this.$refs.searchInput.value = notable_investment;
            this.notableInvestments = [];
        },
        selectIndustry(industry) {
            this.selectedIndustry = industry;
            this.industryList = [];
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
        rejectClaimRequest(id) {
            const csrfToken = document.getElementById("csrf_token").value;

            fetch(`/admin/claim-request/${id}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ status: "rejected" }),
            })
                .then((response) => {
                    if (response.ok) {
                        window.location.reload();
                    }
                })
                .catch((error) => console.error("Error denying claim request:", error));
        },
        approveClaimRequest(id) {
            const csrfToken = document.getElementById("csrf_token").value;

            fetch(`/admin/claim-request/${id}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken,
                },
                body: JSON.stringify({ status: "approved" }),
            })
                .then((response) => {
                    if (response.ok) {
                        window.location.reload();
                    }
                })
                .catch((error) => console.error("Error approving claim request:", error));
        },
        search() {
            const searchQuery = this.searchQuery;
            const params = new URLSearchParams(window.location.search);

            params.delete("page");
            params.delete("type");
            params.delete("msg");

            if (searchQuery) {
                params.set("search", searchQuery);
            } else {
                params.delete("search");
            }

            const newUrl = `${window.location.pathname}?${params.toString()}`;
            window.location.href = newUrl;
            localStorage.setItem("searchQuery", this.searchQuery);
        },
        resetSearchQuery() {
            this.searchQuery = "";
            localStorage.removeItem("searchQuery");
        },
        async getUserList(event) {
            const searchInput = event.target.value;
            if (searchInput.length > 0) {
                const response = await fetch(`/admin/users/search/${searchInput}`);
                if (response.ok) {
                    const data = await response.json();
                    this.userList = data.users;
                }
            } else {
                this.userList = [];
            }
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
        async getNotableInvestments(searchInput) {
            const notableInvestments = this.$refs.notableInvestmentsElement.children;
            const searchTerm = searchInput.toUpperCase();

            for (let item of notableInvestments) {
                item.classList.toggle("hidden", !item.textContent.toUpperCase().includes(searchTerm));
            }
        },
        async fetchData(url) {
            const searchInput = url.split("/").slice(-2, -1)[0].trim();
            if (searchInput.length > 0) {
                const response = await fetch(url);
                if (response.ok) {
                    const data = await response.json();
                    return data.notable_investments || [];
                }
            }
            return [];
        },
        async fetchNotableInvestments(searchInput) {
            if (!searchInput) {
                this.notableInvestments = [];
                return;
            }

            this.notableInvestments = await this.fetchData(
                `/admin/companies/search_notable_investments/${searchInput.trim()}`,
            );
        },
        async fetchNotableInvestmentsByInvestorId(searchInput, investorId) {
            this.notableInvestments = await this.fetchData(
                `/admin/investors/search_notable_investments/${searchInput.trim()}/${investorId}`,
            );
        },
        async fetchNotableInvestmentsByInvestmentFirmId(searchInput, investmentFirmId) {
            this.notableInvestments = await this.fetchData(
                `/admin/investment-firms/search_notable_investments/${searchInput.trim()}/${investmentFirmId}`,
            );
        },
        addNotableInvestment(newInvestment) {
            this.notableInvestments.push(newInvestment);
        },
        debounce(func, wait) {
            let timeout;
            return function (...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        },
        applyFilters() {
            const queryParams = new URLSearchParams({
                ...Object.fromEntries(Object.entries(this.filters).filter(([, value]) => value !== false)),
                page: this.currentPage,
            }).toString();

            const basePath = window.location.pathname.split("/filter")[0];
            window.location.href = `${basePath}/filter?${queryParams}`;
        },
        toggleFundingRound(id) {
            this.selectedFundingRound = this.selectedFundingRound === id ? null : id;
            localStorage.setItem("selectedFundingRound", this.selectedFundingRound);
        },
        toggleInvestment(id) {
            this.selectedInvestment = this.selectedInvestment === id ? null : id;
            localStorage.setItem("selectedInvestment", this.selectedInvestment);
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
        async searchCompanies(event) {
            searchInput = event.target.value;
            let company_list = this.$refs.companyListElement;

            for (let i = 0; i < company_list.children.length; i++) {
                if (company_list.children[i].textContent.toUpperCase().includes(searchInput.toUpperCase())) {
                    company_list.children[i].classList.remove("hidden");
                } else {
                    company_list.children[i].classList.add("hidden");
                }
            }
        },
    },
    mounted() {
        this.setupMenuToggle();
        const urlParams = new URLSearchParams(window.location.search);
        for (const [key, value] of urlParams.entries()) {
            if (key in this.filters) {
                this.filters[key] = value === "true";
            }
            if (key === "page") {
                this.currentPage = parseInt(value) || 1;
            }
        }
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            createNotableInvestmentOpened: false,
            createInvestmentOpened: false,
            deleteInvestmentOpened: false,
            updateInvestmentOpened: false,
            createFundingRoundOpened: false,
            updateFundingRoundOpened: false,
            deleteFundingRoundOpened: false,
            editMemberOpened: false,
            editCompanyMemberOpened: false,
            addMemberOpened: false,
            investment: {},
            csrfToken: "",
            searchQuery: localStorage.getItem("searchQuery") || "",
            selectedRounds: [],
            selectedIndustries: [],
            selectedNotableInvestments: [],
            selectedIndustry: "",
            selectedNotableInvestment: "",
            selectedInvestment: null,
            selectedFundingRound: null,
            userList: [],
            notableInvestments: [],
            industryList: [],
            dataString: "",
            menus: [
                { menu: "industry-options-menu", button: "industry-options" },
                { menu: "round-options-menu", button: "round-options" },
                { menu: "notable-investment-options-menu", button: "notable-investment-options" },
            ],
            showClasses: ["transform", "opacity-100", "scale-100"],
            hideClasses: ["opacity-0", "scale-95", "pointer-events-none"],
            filters: {
                check_about: false,
                check_email: false,
                check_twitter: false,
                check_website: false,
                check_linkedin: false,
                check_instagram: false,
                check_description: false,
                check_industry: false,
                check_rounds: false,
            },
        };
    },
}).mount("#app");
