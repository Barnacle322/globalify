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
    mounted() {
        const lowerSlider = document.getElementById("min_investment");
        const upperSlider = document.getElementById("max_investment");

        if (lowerSlider) {
            lowerSlider.oninput = this.handleLowerSliderInput;
        }

        if (upperSlider) {
            upperSlider.oninput = this.handleUpperSliderInput;
        }

        document.getElementById("search-btn").addEventListener("click", this.search);

        this.setupMenuToggle();
        this.initializeValuesFromParams();
        this.updateLinksWithQueryParams();
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,
            menus: [
                { menu: "industry-options-menu", button: "industry-options" },
                { menu: "country-options-menu", button: "country-options" },
                { menu: "sorting-options-menu", button: "sorting-options" },
                { menu: "filter-options-menu", button: "filter-options" },
                { menu: "round-options-menu", button: "round-options" },
            ],
            showClasses: ["transform", "opacity-100", "scale-100"],
            hideClasses: ["opacity-0", "scale-95", "pointer-events-none"],
        };
    },
    methods: {
        openMenu() {
            document.getElementById("menu").classList.remove("hidden");
        },
        closeMenu() {
            document.getElementById("menu").classList.add("hidden");
        },
        initializeValuesFromParams() {
            const paramsArray = [
                "filter_field",
                "round",
                "industry",
                "sort_field",
                "descending",
                "rounds_exclusive",
                "industries_exclusive",
                "country",
            ];
            paramsArray.forEach((param) => {
                this.setCheckedValuesFromParams(param);
            });
            this.setSearchValueFromParams();
            this.setSliderValuesFromParams("min_investment");
            this.setSliderValuesFromParams("max_investment");
            if (this.openAdvanced) this.toggleAdvanced();
        },
        setCheckedValuesFromParams(inputName) {
            const urlParams = new URLSearchParams(window.location.search);
            const values = urlParams.getAll(inputName);

            values.forEach((value) => {
                this.openAdvanced = true;
                const checkbox = document.querySelector(`input[name="${inputName}"][value="${value}"]`);
                if (checkbox) checkbox.checked = true;
            });
        },
        setSliderValuesFromParams(sliderId) {
            const urlParams = new URLSearchParams(window.location.search);
            const value = urlParams.get(sliderId);

            if (value !== null) {
                this.openAdvanced = true;
                const percentage = (value / 50000000) * 100;
                document.getElementById(sliderId).value = percentage;
            }
        },
        setSearchValueFromParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const value = urlParams.get("search");

            if (value !== null) {
                this.openAdvanced = true;
                document.getElementById("search").value = value;
            }
        },
        toggleAdvanced() {
            const advancedMenu = document.getElementById("advanced-menu");

            const openedAdvanced = document.getElementById("opened-advanced");
            const closedAdvanced = document.getElementById("closed-advanced");

            if (advancedMenu.classList.contains("hidden")) {
                advancedMenu.classList.remove("hidden");
                advancedMenu.classList.add("flex");

                openedAdvanced.classList.remove("hidden");
                closedAdvanced.classList.add("hidden");
            } else {
                advancedMenu.classList.add("hidden");
                advancedMenu.classList.remove("flex");

                openedAdvanced.classList.add("hidden");
                closedAdvanced.classList.remove("hidden");
            }
        },
        search() {
            const roundValues = this.getCheckedValues("round");
            const industryValues = this.getCheckedValues("industry");
            const countryValues = this.getCheckedValues("country");
            const sortValues = this.getCheckedValues("sort_field");
            const filterValues = this.getCheckedValues("filter_field");

            const searchQuery = document.getElementById("search").value;
            const minValueElement = document.getElementById("min_investment");
            const minValue = minValueElement ? minValueElement.value : 0;

            const maxValueElement = document.getElementById("max_investment");
            const maxValue = maxValueElement ? maxValueElement.value : 100;

            const descendingElement = document.getElementById("descending");
            const descending = descendingElement ? descendingElement.checked : false;

            const roundsExclusiveElement = document.getElementById("rounds_exclusive");
            const roundsExclusive = roundsExclusiveElement ? roundsExclusiveElement.checked : false;

            const industriesExclusiveElement = document.getElementById("industries_exclusive");
            const industriesExclusive = industriesExclusiveElement ? industriesExclusiveElement.checked : false;

            const paramsArray = this.getExistingParams([
                "search",
                "filter_field",
                "rounds_exclusive",
                "industries_exclusive",
                "round",
                "industry",
                "country",
                "sort_field",
                "descending",
                "page",
                "min_investment",
                "max_investment",
            ]);

            this.handleLists(roundValues, "round", paramsArray);
            this.handleLists(industryValues, "industry", paramsArray);
            this.handleLists(countryValues, "country", paramsArray);
            this.handleLists(sortValues, "sort_field", paramsArray);
            this.handleLists(filterValues, "filter_field", paramsArray);

            this.handleInvestmentRange(minValue, "min_investment", paramsArray);
            this.handleInvestmentRange(maxValue, "max_investment", paramsArray);

            this.handleBooleans(roundsExclusive, "rounds_exclusive", paramsArray);
            this.handleBooleans(industriesExclusive, "industries_exclusive", paramsArray);
            this.handleBooleans(descending, "descending", paramsArray);

            if (searchQuery !== "") paramsArray.unshift(`search=${encodeURIComponent(searchQuery)}`);

            this.addParamsToUrl(paramsArray);
        },
        getCheckedValues(inputName) {
            const checkboxes = document.querySelectorAll(`input[name="${inputName}"]:checked`);
            return Array.from(checkboxes).map((checkbox) => checkbox.value);
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
        handleLists(values, paramName, paramsArray) {
            values.forEach((value) => paramsArray.push(`${paramName}=${encodeURIComponent(value)}`));
        },
        handleInvestmentRange(value, paramName, paramsArray) {
            if (value == 0 || value == 100) return;
            if (value !== "") {
                const actualValue = Math.floor((value / 100) * 50000000);
                paramsArray.push(`${paramName}=${encodeURIComponent(actualValue)}`);
            }
        },
        handleBooleans(value, paramName, paramsArray) {
            if (value) {
                paramsArray.push(`${paramName}=${value ? 1 : ""}`);
            }
        },
        addParamsToUrl(paramsArray) {
            const paramsString = paramsArray.length > 0 ? "?" + paramsArray.join("&") : "";
            const baseUrl = window.location.href.split("?")[0];
            const newUrl = baseUrl + paramsString;

            window.location.href = newUrl;
        },
        handleLowerSliderInput() {
            const lowerSlider = document.getElementById("min_investment");
            const upperSlider = document.getElementById("max_investment");

            if (parseInt(lowerSlider.value) >= parseInt(upperSlider.value)) {
                lowerSlider.value = parseInt(upperSlider.value) - 9;
            }
        },
        handleUpperSliderInput() {
            const lowerSlider = document.getElementById("min_investment");
            const upperSlider = document.getElementById("max_investment");

            if (parseInt(upperSlider.value) <= parseInt(lowerSlider.value)) {
                upperSlider.value = parseInt(lowerSlider.value) + 9;
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
        getQueryParams() {
            return new URLSearchParams(window.location.search);
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
        updateLinksWithQueryParams() {
            document.querySelectorAll('a[href^="/"]:not([href^="//"])').forEach((link) => {
                if (!link.getAttribute("href").includes("search")) return;
                link.setAttribute("href", this.applyQueryParams(link.getAttribute("href")));
            });
        },
        async toggleInvestorBookmark(investorId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investor/${investorId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    const data = await response.json();
                    var svg = document.getElementById(`bookmark-svg-investor-${investorId}`);
                    if (data[0].bookmarked) {
                        svg.style.fill = "#FFC9FC";
                    } else {
                        svg.style.fill = "none";
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async toggleInvestmentFirmBookmark(firmId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/investment-firm/${firmId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    const data = await response.json();
                    var svg = document.getElementById(`bookmark-svg-firm-${firmId}`);
                    if (data[0].bookmarked) {
                        svg.style.fill = "#FFC9FC";
                    } else {
                        svg.style.fill = "none";
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async markAsRead(notificationId) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const response = await fetch(`/notification/mark-read/${notificationId}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (!response.ok) {
                    console.error("An error occurred while marking the notification as read.");
                }
            } catch (error) {
                console.error(error);
            }
        },
    },
}).mount("#app");
