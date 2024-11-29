createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        Bookmark,
        CreateNotableInvestmentComponent,
        CreateInvestmentComponent,
        DeleteInvestmentComponent,
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
        async submitInvestmentData() {
            const csrfToken = document.getElementById("csrf_token").value;

            const investor_id = document.getElementById("investor").value;
            const investment_firm_id = document.getElementById("investment_firm").value;
            const funding_round_id = document.getElementById("funding_round").value;
            const createdByAdminElement = document.getElementById("created_by_admin");
            const created_by_admin = createdByAdminElement ? createdByAdminElement.checked : false;
            const isVerifiedElement = document.getElementById("is_verified");
            const is_verified = isVerifiedElement ? isVerifiedElement.checked : false;

            const dataString = JSON.stringify({
                investor_id: investor_id,
                investment_firm_id: investment_firm_id,
                funding_round_id: funding_round_id,
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
            const round_id = document.getElementById("round").value;
            const announced_date = document.getElementById("announced_date").value;

            const dataString = JSON.stringify({
                company_id: company_id,
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
    },
    mounted() {
        this.setupMenuToggle();
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            createNotableInvestmentOpened: false,
            createInvestmentOpened: false,
            deleteInvestmentOpened: false,
            csrfToken: "",
            searchQuery: localStorage.getItem("searchQuery") || "",
            selectedRounds: [],
            selectedIndustries: [],
            selectedNotableInvestments: [],
            selectedIndustry: "",
            selectedNotableInvestment: "",
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
        };
    },
}).mount("#app");
