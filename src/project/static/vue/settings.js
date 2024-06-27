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

createApp({
    emits: ["close-confirm-restore"],
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        Bookmark,
        ConfirmRestoreComponent,
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
    },
    created() {
        this.asideMinified = localStorage.getItem("asideMinified") === "true";
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            confirmRestoreOpened: false,
            csrfToken: "",
            selectedRounds: [],
            selectedIndustries: [],
            selectedNotableInvestments: [],
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
    },
    mounted() {
        this.setupMenuToggle();

        var industryList = document.querySelector("#industry-options-menu .py-1");
        var industryItems = Array.from(industryList.children);
        industryItems.sort(function (a, b) {
            var aChecked = a.querySelector("input") ? a.querySelector("input").checked : false;
            var bChecked = b.querySelector("input") ? b.querySelector("input").checked : false;
            return aChecked === bChecked ? 0 : aChecked ? -1 : 1;
        });
        industryItems.forEach(function (item) {
            industryList.appendChild(item);
        });

        var searchInputIndustries = document.getElementById("search-industries");
        searchInputIndustries.addEventListener("input", function () {
            var filter = searchInputIndustries.value.toUpperCase();
            for (var i = 0; i < industryItems.length; i++) {
                var item = industryItems[i];
                var text = item.textContent || item.innerText;
                if (text.toUpperCase().indexOf(filter) > -1) {
                    item.style.display = "";
                } else {
                    item.style.display = "none";
                }
            }
        });

        var notableInvestmentList = document.querySelector("#notable-investment-options-menu .py-1");
        var notableInvestmentItems = Array.from(notableInvestmentList.children);
        notableInvestmentItems.sort(function (a, b) {
            var aChecked = a.querySelector("input") ? a.querySelector("input").checked : false;
            var bChecked = b.querySelector("input") ? b.querySelector("input").checked : false;
            return aChecked === bChecked ? 0 : aChecked ? -1 : 1;
        });
        notableInvestmentItems.forEach(function (item) {
            notableInvestmentList.appendChild(item);
        });

        var searchInputNotableInvestments = document.getElementById("search-notable-investments");
        searchInputNotableInvestments.addEventListener("keyup", function () {
            var filter = searchInputNotableInvestments.value.toUpperCase();
            notableInvestmentItems.forEach(function (item) {
                var text = item.textContent || item.innerText;
                item.style.display = text.toUpperCase().indexOf(filter) > -1 ? "" : "none";
            });
        });
    },
}).mount("#app");
