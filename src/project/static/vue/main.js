const FullInvestor = defineComponent({
    template: "#full-investor-template",
    props: { slug: String, rendercontacts: Boolean },
    emits: ["close-investor", "bookmarked"],
    delimiters: ["[[", "]]"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteInvestorParam();
        document.removeEventListener("click", this.handleClickOutside);
        const script_element = document.getElementById("twitter-script");
        if (script_element) script_element.remove();
    },
    async created() {
        await this.fetchInvestor();
        window.removeEventListener("popstate", this.checkUrlParams);
        this.fetchInvestments(this.investor.id);
    },
    methods: {
        async fetchInvestor() {
            try {
                const response = await fetch(`/investor/${this.slug}/get`);
                if (response.ok) {
                    const data = await response.json();
                    this.investor = data.investor;
                    this.isBookmarked = data.isBookmarked;
                    this.unpaid = data.unpaid;
                    await this.loadTwitterTimeline();
                } else {
                    this.closeInvestor();
                    return;
                }
            } catch (error) {
                console.error("Error fetching investor:", error);
                this.closeInvestor();
            } finally {
                this.isLoading = false;
            }
        },
        async loadTwitterTimeline() {
            if (!this.investor?.twitter) return;
            this.loadingTwitter = true; // Set loading state to true
            this.ensureTwitterScriptLoaded(() => {
                const timeline = document.querySelector(".twitter-timeline");
                if (timeline) {
                    timeline.innerHTML = "";
                    timeline.setAttribute("href", this.investor.twitter);
                    window.twttr?.widgets.load();

                    const observer = new MutationObserver((mutations) => {
                        mutations.forEach((mutation) => {
                            const twitterWidget = document.querySelector("[id^='twitter-widget-']");
                            if (twitterWidget && twitterWidget.offsetHeight > 0) {
                                this.loadingTwitter = false;
                                observer.disconnect();
                            }
                        });
                    });

                    observer.observe(document.body, { childList: true, subtree: true });
                }
            });
        },
        ensureTwitterScriptLoaded(callback) {
            const script_element = document.getElementById("twitter-script");
            if (script_element) script_element.remove();

            if (!this.twitterScriptLoaded) {
                const script = document.createElement("script");
                script.src = "https://platform.twitter.com/widgets.js";
                script.id = "twitter-script";
                script.async = true;
                script.onload = () => {
                    this.twitterScriptLoaded = true;
                    callback();
                };
                document.body.appendChild(script);
            } else {
                callback();
            }
        },
        async toggleBookmark(investorId) {
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
                        this.$emit("bookmarked", { investorId: investorId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        // svg.style.fill = "none";
                        this.$emit("bookmarked", { investorId: investorId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async fetchInvestments(investorId) {
            try {
                const response = await fetch(`/investment/${investorId}/get`);
                if (response.ok) {
                    const data = await response.json();
                    this.investments = data.investments;

                    this.n_of_investments = data.n_of_investments;
                }
            } catch (error) {
                console.error(error);
            }
        },
        async sortInvestments(sortType) {
            const compareDates = (a, b) => {
                const dateA = new Date(a.announced_date);
                const dateB = new Date(b.announced_date);
                return sortType === "asc" ? dateA - dateB : dateB - dateA;
            };

            this.investments.sort(compareDates);

            // Force re-render
            this.investments = [...this.investments];
            this.sortOrder = sortType;
            this.sortDropdownOpened = false;
        },
        deleteInvestorParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("investor");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("investor");
            if (!investorSlug) {
                this.$emit("close-investor");
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-investor");
            }
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        closeInvestor() {
            this.$emit("close-investor");
        },
        getTwitterHandle(url) {
            return url.split("/").pop();
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            showPopover: false,
            isExpanded: false,
            isLoading: true,
            isBookmarked: false,
            investor: null,
            unpaid: false,
            sortDropdownOpened: false,
            sortOrder: null,
            investments: [],
            dropdownOpened: false,
            twitterScriptLoaded: false,
            loadingTwitter: false,
        };
    },
});

const SearchHistory = defineComponent({
    template: "#search-history-template",
    delimiters: ["[[", "]]"],
    props: ["type"],
    async mounted() {
        try {
            const response = await fetch(`/search-history?type=${this.type}&page=1&limit=5`);
            if (response.ok) {
                const data = await response.json();
                for (let item of data) {
                    this.searchHistoryData.push(...item.histories);
                }
            } else {
                console.error("An error occurred while fetching the search history.");
            }
        } catch (error) {
            console.error(error);
        }
    },
    data() {
        return {
            searchHistoryData: [],
        };
    },
});

const FullInvestmentFirm = defineComponent({
    template: "#full-investment-firm-template",
    props: { slug: String },
    emits: ["close-investment-firm", "bookmarked"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteInvestmentFirmParam();
        document.removeEventListener("click", this.handleClickOutside);
    },
    async created() {
        await this.fetchInvestmentFirm();
        window.removeEventListener("popstate", this.checkUrlParams);
        this.fetchInvestments(this.investmentFirm.id);
    },
    methods: {
        async fetchInvestmentFirm() {
            this.isLoading = true;
            try {
                const response = await fetch(`/investment-firm/${this.slug}`);
                if (response.ok) {
                    const data = await response.json();
                    this.investmentFirm = data.investment_firm;
                    this.unpaid = data.unpaid;
                    this.isBookmarked = data.isBookmarked;
                } else {
                    this.closeInvestmentFirm();
                    return;
                }
            } catch (error) {
                console.error("Error fetching investment firm:", error);
            } finally {
                this.isLoading = false;
            }
        },
        async toggleBookmark(firmId) {
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
                        this.$emit("bookmarked", { firmId: firmId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        this.$emit("bookmarked", { firmId: firmId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async fetchInvestments(firmId) {
            try {
                const response = await fetch(`/investment-firm/investment/${firmId}/get`);
                if (response.ok) {
                    const data = await response.json();
                    this.investments = data.investments;
                }
            } catch (error) {
                console.error(error);
            }
        },
        async sortInvestments(sortType) {
            const compareDates = (a, b) => {
                const dateA = new Date(a.announced_date);
                const dateB = new Date(b.announced_date);
                return sortType === "asc" ? dateA - dateB : dateB - dateA;
            };

            this.investments.sort(compareDates);

            // Force re-render
            this.investments = [...this.investments];
            this.sortOrder = sortType;
            this.sortDropdownOpened = false;
        },
        getTwitterHandle(url) {
            if (!url) return;
            return url.split("/").pop();
        },
        deleteInvestmentFirmParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("investment-firm");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("investment-firm");
            if (!investorSlug) {
                this.$emit("close-investment-firm");
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-investment-firm");
            }
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        сloseInvestmentFirm() {
            this.$emit("close-investment-firm");
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            investmentFirm: null,
            isBookmarked: false,
            unpaid: false,
            sortDropdownOpened: false,
            sortOrder: null,
            investments: [],
            dropdownOpened: false,
        };
    },
});

const FullCompany = defineComponent({
    template: "#full-company-template",
    props: { slug: String },
    emits: ["close-company", "bookmarked"],
    delimiters: ["[[", "]]"],
    mounted() {
        window.addEventListener("keydown", this.handleKeyDown);
        document.addEventListener("click", this.handleClickOutside);
    },
    beforeUnmount() {
        window.removeEventListener("keydown", this.handleKeyDown);
        this.deleteCompanyParam();
        document.removeEventListener("click", this.handleClickOutside);
    },
    async created() {
        await this.fetchCompany();
        window.removeEventListener("popstate", this.checkUrlParams);
        this.fetchInvestments(this.company.id);
    },
    methods: {
        async fetchCompany() {
            this.isLoading = true;
            try {
                const response = await fetch(`/company/${this.slug}`);
                if (response.ok) {
                    const data = await response.json();
                    this.company = data.company;
                    this.unpaid = data.unpaid;
                    this.isBookmarked = data.isBookmarked;
                } else {
                    this.closeCompany();
                    return;
                }
            } catch (error) {
                console.error("Error fetching company:", error);
            } finally {
                this.isLoading = false;
            }
        },
        async toggleBookmark(companyId) {
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
                    var svg = document.getElementById(`bookmark-svg-company-${companyId}`);
                    if (data[0].bookmarked) {
                        this.$emit("bookmarked", { companyId: companyId, status: true });
                        this.isBookmarked = !this.isBookmarked;
                    } else {
                        svg.style.fill = "none";
                        this.$emit("bookmarked", { companyId: companyId, status: false });
                        this.isBookmarked = !this.isBookmarked;
                    }
                }
            } catch (error) {
                console.error(error);
            }
        },
        async fetchInvestments(companyId) {
            try {
                const response = await fetch(`/company/investment/${companyId}/get`);
                if (response.ok) {
                    const data = await response.json();
                    this.investments = data.investments;
                }
            } catch (error) {
                console.error(error);
            }
        },
        async sortInvestments(sortType) {
            const compareDates = (a, b) => {
                const dateA = new Date(a.announced_date);
                const dateB = new Date(b.announced_date);
                return sortType === "asc" ? dateA - dateB : dateB - dateA;
            };

            this.investments.sort(compareDates);

            // Force re-render
            this.investments = [...this.investments];
            this.sortOrder = sortType;
            this.sortDropdownOpened = false;
        },
        deleteCompanyParam() {
            const url = new URL(window.location.href);
            url.searchParams.delete("company");
            window.history.replaceState({}, "", url);
        },
        checkUrlParams() {
            const urlParams = new URLSearchParams(window.location.search);
            const investorSlug = urlParams.get("company");
            if (!investorSlug) {
                this.$emit("close-company");
            }
        },
        handleKeyDown(event) {
            if (event.key === "Escape") {
                this.$emit("close-company");
            }
        },
        getTwitterHandle(url) {
            if (!url) return;
            return url.split("/").pop();
        },
        toggleExpansion() {
            this.isExpanded = !this.isExpanded;
        },
        closeCompany() {
            this.$emit("close-company");
        },
        handleClickOutside(event) {
            const dropdownContainer = this.$refs.dropdownContainer;
            if (dropdownContainer && !dropdownContainer.contains(event.target)) {
                this.dropdownOpened = false;
            }
        },
    },
    data() {
        return {
            isExpanded: false,
            isLoading: false,
            isBookmarked: false,
            company: null,
            unpaid: false,
            sortDropdownOpened: false,
            sortOrder: null,
            investments: [],
            dropdownOpened: false,
        };
    },
});

const app = createApp({
    components: {
        AsideComponent,
        AsideMobileComponent,
        NavbarComponent,
        FullInvestor,
        FullInvestmentFirm,
        FullCompany,
        SearchHistory,
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
        // posthog.capture("App Loaded");
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
        window.addEventListener("click", this.closeSortDropdownOutside);
        window.addEventListener("scroll", this.handleScroll);
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
                const response = await fetch("/bookmarks/investor");
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
                const response = await fetch("/bookmarks/investment-firm");
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
                const response = await fetch("/bookmarks/company");
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
            const urlParams = new URLSearchParams(window.location.search);

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
            paramsArray.forEach((inputName) => {
                const values = urlParams.getAll(inputName);
                values.forEach((value) => {
                    this.openAdvanced = true;
                    const checkbox = document.querySelector(`input[name="${inputName}"][value="${value}"]`);
                    if (checkbox) checkbox.checked = true;
                });
            });

            const value = urlParams.get("search");
            if (value !== null) {
                this.openAdvanced = true;
                document.getElementById("search").value = value;
            }

            this.setSliderValuesFromParams("min_investment");
            this.setSliderValuesFromParams("max_investment");
            if (this.openAdvanced) this.toggleAdvanced();
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
        search(query = "") {
            const roundValues = this.getCheckedValues("round");
            const industryValues = this.getCheckedValues("industry");
            const countryValues = this.getCheckedValues("country");
            const sortValues = this.getCheckedValues("sort_field");
            const filterValues = this.getCheckedValues("filter_field");

            let searchQuery = document.getElementById("search").value;
            if (!searchQuery && typeof query == "string") {
                searchQuery = query;
            }

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

            const paramsString = paramsArray.length > 0 ? "?" + paramsArray.join("&") : "";
            const baseUrl = window.location.href.split("?")[0];
            const newUrl = baseUrl + paramsString;

            window.location.href = newUrl;
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
        applyQueryParams(url) {
            const params = new URLSearchParams(window.location.search);
            params.delete("page");
            params.delete("investor");
            params.delete("company");

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
        closeSortDropdownOutside() {
            this.sortDropdownOpened = false;
        },
        showSearchHistory() {
            this.isSearchHistoryVisible = true;
        },
        hideSearchHistory() {
            // Delay hiding to allow click event to be registered
            setTimeout(() => {
                this.isSearchHistoryVisible = false;
            }, 200);
        },
    },
    data() {
        return {
            asideExpanded: false,
            asideMinified: false,
            openAdvanced: false,
            isSearchHistoryVisible: false,
            selectedInvestorSlug: null,
            selectedInvestmentFirmSlug: null,
            selectedCompanySlug: null,
            bookmarkedInvestorId: null,
            investmentInvestorId: null,
            n_of_investments: 0,
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
                { menu: "round-options-menu", button: "round-options" },
            ],
            showClasses: ["transform", "opacity-100", "scale-100"],
            hideClasses: ["opacity-0", "scale-95", "pointer-events-none"],
        };
    },
});

// app.use(posthogPlugin);

app.mount("#app");
