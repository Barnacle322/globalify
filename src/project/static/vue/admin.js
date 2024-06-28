createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        Bookmark,
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
    },
    created() {
        this.asideMinified = localStorage.getItem("asideMinified") === "true";
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            csrfToken: "",
            selectedRounds: [],
            selectedIndustries: [],
            selectedNotableInvestments: [],
            selectedEmail: "",
            selectedIndustry: "",
            selectedNotableInvestments: "",
            userList: [],
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
    methods: {
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

            let dataString = JSON.stringify({
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
        async deleteInvestor(id) {
            const csrfToken = document.getElementById("csrf_token").value;

            if (!confirm("Are you sure you want to delete this investor?")) {
                return;
            }

            const response = await fetch(`/admin/investor/${id}/delete`, {
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
        async undoInvestorData(investorId) {
            const csrfToken = document.getElementById("csrf_token").value;

            try {
                const response = await fetch(`/admin/investor/${investorId}/undo`, {
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
                const response = await fetch(`/admin/investor/${investorId}/restore`, {
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

            const dataString = JSON.stringify({
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
        async deleteInvestmentFirm(id) {
            const csrfToken = document.getElementById("csrf_token").value;

            if (!confirm("Are you sure you want to delete this investment firm?")) {
                return;
            }

            const response = await fetch(`/admin/investment-firm/${id}/delete`, {
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
            this.selectedEmail = email;
            this.userList = [];
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

        // search section
        search() {
            const searchQuery = document.getElementById("search").value;

            const paramsArray = this.getExistingParams(["search", "page"]);

            if (searchQuery !== "") paramsArray.unshift(`search=${encodeURIComponent(searchQuery)}`);

            this.addParamsToUrl(paramsArray);
        },
        getExistingParams(excludedParams) {
            const urlParams = new URLSearchParams(window.location.search);
            let paramsArray = [];

            for (let param of urlParams) {
                if (!excludedParams.includes(param[0])) {
                    paramsArray.push(`${param[0]}=${encodeURIComponent(param[1])}`);
                }
            }
            return paramsArray;
        },
        addParamsToUrl(paramsArray) {
            const paramsString = paramsArray.length > 0 ? "?" + paramsArray.join("&") : "";
            const baseUrl = window.location.href.split("?")[0];
            const newUrl = baseUrl + paramsString;
            window.location.href = newUrl;
        },
        getQueryParams() {
            params = new URLSearchParams(window.location.search);
            params.delete("type");
            params.delete("msg");
            return params;
        },
        removePageParam(params) {
            params.delete("page");
            return params;
        },
        applyQueryParams(url) {
            const params = this.removePageParam(this.getQueryParams());
            if (params.toString()) {
                return `${url}${url.includes("?") ? "&" : "?"}${params.toString()}`;
            }
            return url;
        },
        async getUserList(searchInput) {
            if (searchInput.length > 0) {
                const response = await fetch(`/admin/search_users/${searchInput}`);
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
    },
    mounted() {
        this.setupMenuToggle();

        // var notableInvestmentList = document.querySelector("#notable-investment-options-menu .py-1");

        // if (notableInvestmentList) {
        //     var notableInvestmentItems = Array.from(notableInvestmentList.children);
        //     notableInvestmentItems.sort(function (a, b) {
        //         var aChecked = a.querySelector("input") ? a.querySelector("input").checked : false;
        //         var bChecked = b.querySelector("input") ? b.querySelector("input").checked : false;
        //         return aChecked === bChecked ? 0 : aChecked ? -1 : 1;
        //     });
        //     notableInvestmentItems.forEach(function (item) {
        //         notableInvestmentList.appendChild(item);
        //     });

        //     var searchInputNotableInvestments = document.getElementById("search-notable-investments");
        //     searchInputNotableInvestments.addEventListener("keyup", function () {
        //         var filter = searchInputNotableInvestments.value.toUpperCase();
        //         notableInvestmentItems.forEach(function (item) {
        //             var text = item.textContent || item.innerText;
        //             item.style.display = text.toUpperCase().indexOf(filter) > -1 ? "" : "none";
        //         });
        //     });
        // }

        // search
        document.querySelectorAll('a[href^="/"]:not([href^="//"])').forEach((link) => {
            if (!link.getAttribute("href").includes("admin")) return;
            link.setAttribute("href", this.applyQueryParams(link.getAttribute("href")));
        });
    },
}).mount("#app");
