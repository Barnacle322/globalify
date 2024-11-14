createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        Bookmark,
        FullInvestor,
        FullInvestmentFirm,
        FullCompany,
        SearchHistory
    },
    watch: {
        asideMinified(value) {
            localStorage.setItem("asideMinified", value);
        },
        selectedInvestorId(value) {
            if (value) {
                document.body.classList.add("overflow-hidden");
            } else {
                document.body.classList.remove("overflow-hidden");
            }
        },
        selectedInvestmentFirmId(value) {
            if (value) {
                document.body.classList.add("overflow-hidden");
            } else {
                document.body.classList.remove("overflow-hidden");
            }
        },
    },
    created() {
        this.asideMinified = localStorage.getItem("asideMinified") === "true";
        window.addEventListener("popstate", this.checkUrlParams("investor", this.selectInvestorSlug, "close-investor"));
        window.addEventListener(
            "popstate",
            this.checkUrlParams("investment-firm", this.selectInvestmentFirmSlug, "close-investment-firm"),
        );
        window.addEventListener("popstate", this.checkUrlParams("company", this.selectCompanySlug, "close-company"));
        this.checkAndSelectUrlParam("investor", this.selectInvestorSlug);
        this.checkAndSelectUrlParam("investment-firm", this.selectInvestmentFirmSlug);
        this.checkAndSelectUrlParam("company", this.selectCompanySlug);
        this.fetchInvestorBookmarks();
        this.fetchInvestmentFirmBookmarks();
        this.fetchCompanyBookmarks();
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

        const searchBtn = document.getElementById("search-btn");
        if (searchBtn) {
            searchBtn.addEventListener("click", this.search);
        }

        this.setupMenuToggle();
        this.initializeValuesFromParams();
        this.updateLinksWithQueryParams();
        window.addEventListener("popstate", this.checkUrlParams("investor", this.selectInvestorSlug, "close-investor"));
        window.addEventListener(
            "popstate",
            this.checkUrlParams("investment-firm", this.selectInvestmentFirmSlug, "close-investment-firm"),
        );
        window.addEventListener("popstate", this.checkUrlParams("company", this.selectCompanySlug, "close-company"));
    },
    updated() {
        window.addEventListener("popstate", this.checkUrlParams("investor", this.selectInvestorSlug, "close-investor"));
        window.addEventListener(
            "popstate",
            this.checkUrlParams("investment-firm", this.selectInvestmentFirmSlug, "close-investment-firm"),
        );
        window.addEventListener("popstate", this.checkUrlParams("company", this.selectCompanySlug, "close-company"));
    },
    methods: {
        async handleInvestorBookmark(data) {
            try {
                if (data.status) {
                    this.investorBookmakrIds.push(data.investorId); // Corrected typo
                } else {
                    this.investorBookmakrIds = this.investorBookmakrIds.filter((id) => id !== data.investorId); // Corrected typo
                }
            } catch (error) {
                console.error("Error handling investor bookmark:", error);
            }
        },
        async fetchInvestorBookmarks() {
            try {
                const response = await fetch("/investor/bookmarks");
                if (response.ok) {
                    const data = await response.json();
                    this.investorBookmakrIds = data.bookmark_ids;
                }
            } catch (error) {
                console.error(error);
            }
        },
        async handleInvestmentFirmBookmark(data) {
            if (data.status) {
                this.investmentFirmBookmakrIds.push(data.firmId);
            } else {
                this.investmentFirmBookmakrIds = this.investmentFirmBookmakrIds.filter((id) => id !== data.firmId);
            }
        },
        async fetchInvestmentFirmBookmarks() {
            try {
                const response = await fetch("/investment-firm/bookmarks");
                if (response.ok) {
                    const data = await response.json();
                    this.investmentFirmBookmakrIds = data.bookmark_ids;
                }
            } catch (error) {
                console.error(error);
            }
        },
        async handleCompanyBookmark(data) {
            try {
                if (data.status) {
                    this.companyBookmarkIds.push(data.companyId);
                } else {
                    this.companyBookmarkIds = this.companyBookmarkIds.filter((id) => id !== data.companyId);
                }
            } catch (error) {
                console.error("Error handling company bookmark:", error);
            }
        },
        async fetchCompanyBookmarks() {
            try {
                const response = await fetch("/company/bookmarks");
                if (response.ok) {
                    const data = await response.json();
                    this.companyBookmarkIds = data.bookmark_ids;
                }
            } catch (error) {
                console.error(error);
            }
        },
        checkAndSelectUrlParam(paramName, selectFunction) {
            const urlParams = new URLSearchParams(window.location.search);
            const paramSlug = urlParams.get(paramName);
            if (paramSlug) {
                selectFunction(paramSlug);
            }
        },
        checkUrlParams(paramName, selectFunction, closeEvent) {
            const urlParams = new URLSearchParams(window.location.search);
            let paramSlug = urlParams.get(paramName);
            if (paramSlug) {
                if (typeof paramSlug === "object" && paramSlug !== null) {
                    paramSlug = paramSlug;
                }
                selectFunction(paramSlug);
            } else {
                this.$emit(closeEvent);
            }
        },
        updateUrlParam(paramName, paramValue, stateKey) {
            const url = new URL(window.location.href);
            if (url.searchParams.get(paramName) !== paramValue) {
                url.searchParams.set(paramName, paramValue);
                window.history.pushState({}, "", url);
            }
            this[stateKey] = paramValue;
        },
        selectInvestorSlug(investorSlug) {
            this.updateUrlParam("investor", investorSlug, "selectedInvestorSlug");
        },
        selectInvestmentFirmSlug(investmentFirmSlug) {
            this.updateUrlParam("investment-firm", investmentFirmSlug, "selectedInvestmentFirmSlug");
        },
        selectCompanySlug(companySlug) {
            this.updateUrlParam("company", companySlug, "selectedCompanySlug");
        },
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
                "max_investment"
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
            params.delete("investor");
            params.delete("company");
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
            document.querySelectorAll("a[href^=\"/\"]:not([href^=\"//\"])").forEach((link) => {
                if (!link.getAttribute("href").includes("search")) return;
                link.setAttribute("href", this.applyQueryParams(link.getAttribute("href")));
            });
        },
        async getCountryList(searchInput) {
            let country_list = this.$refs.countryListElement;
            for (let i = 0; i < country_list.children.length; i++) {
                if (country_list.children[i].textContent.toUpperCase().includes(searchInput.toUpperCase())) {
                    country_list.children[i].classList.remove("hidden");
                } else {
                    country_list.children[i].classList.add("hidden");
                }
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
                    if (data[0].bookmarked) {
                        this.investorBookmakrIds.push(investorId);
                    } else {
                        this.investorBookmakrIds = this.investorBookmakrIds.filter((id) => id !== investorId);
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
                    if (data[0].bookmarked) {
                        this.investmentFirmBookmakrIds.push(firmId);
                    } else {
                        this.investmentFirmBookmakrIds = this.investmentFirmBookmakrIds.filter((id) => id !== firmId);
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async toggleCompanyBookmark(companyId) {
            const csrfToken = document.getElementById("csrf_token").value;
            try {
                const response = await fetch(`/company/${companyId}/bookmark`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken,
                    },
                });
                if (response.ok) {
                    const data = await response.json();
                    if (data[0].bookmarked) {
                        this.companyBookmarkIds.push(companyId);
                    } else {
                        this.companyBookmarkIds = this.companyBookmarkIds.filter((id) => id !== companyId);
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
                        "X-CSRFToken": csrfToken
                    }
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
        async getSearchHistory(type) {
            try {
                const csrfToken = document.getElementById("csrf_token").value;
                const url = new URL(`/search_history`, window.location.origin);
                url.searchParams.append("type", type);
                const response = await fetch(url, {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrfToken
                    },
                });
                if (response.redirected) {
                    window.location.href = response.url;
                } else if (!response.ok) {
                    console.error("An error occurred while marking the notification as read.");
                } else {
                    const data = await response.json();
                    this.searchHistoryData = data;
                }
            } catch (error) {
                console.error(error);
            }
        },
        handleSearchHistory(type) {
            this.getSearchHistory(type).then(() => {
                this.isSearchHistoryVisible = !this.isSearchHistoryVisible;
            }).catch(error => {
                console.error("An error occurred in handleSearchHistory:", error);
            });
        }
    },


    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,

            isSearchHistoryVisible: false,
            searchHistoryData: [],

            selectedInvestorSlug: null,
            selectedInvestmentFirmSlug: null,
            selectedCompanySlug: null,
            bookmarkedInvestorId: null,
            investorBookmakrIds: [],
            investmentFirmBookmakrIds: [],
            companyBookmarkIds: [],
            selectedIndustry: "",
            selectedCountry: "",
            menus: [
                { menu: "industry-options-menu", button: "industry-options" },
                { menu: "country-options-menu", button: "country-options" },
                { menu: "sorting-options-menu", button: "sorting-options" },
                { menu: "filter-options-menu", button: "filter-options" },
                { menu: "round-options-menu", button: "round-options" }
            ],
            showClasses: ["transform", "opacity-100", "scale-100"],
            hideClasses: ["opacity-0", "scale-95", "pointer-events-none"]
        };
    }
}).mount("#app");
