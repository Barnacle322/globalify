let user_menu = document.getElementById("user-menu");
let user_menu_button = document.getElementById("user-menu-button");

// Add a click event listener to the document object
document.addEventListener("click", (event) => {
    // Check if the clicked element is not inside the user_menu div
    if (!user_menu.contains(event.target) && !user_menu_button.contains(event.target)) {
        // If the clicked element is outside the user_menu div, close the div
        user_menu.classList.remove("transform", "opacity-100", "scale-100");
        user_menu.classList.add("opacity-0", "scale-95", "pointer-events-none");
    }
});

user_menu_button.onclick = () => {
    if (user_menu.classList.contains("opacity-0")) {
        user_menu.classList.add("transform", "opacity-100", "scale-100");
        user_menu.classList.remove("opacity-0", "scale-95", "pointer-events-none");
    } else {
        user_menu.classList.remove("transform", "opacity-100", "scale-100");
        user_menu.classList.add("opacity-0", "scale-95", "pointer-events-none");
    }
};

$(document).ready(function () {
    var urlParams = new URLSearchParams(window.location.search);
    var selectedRounds = urlParams.getAll('round');
    var selectedIndustries = urlParams.getAll('industry');
    var selectedFields = urlParams.getAll('sort_field');
    var selectedSort = urlParams.getAll('descending');
    var dropdown = $('.checkbox-dropdown .checkbox-options');

    selectedRounds.forEach(function(round) {
        $('.filter-round-checkbox[value="' + round + '"]').prop('checked', true);
    });

    selectedIndustries.forEach(function(industry) {
        $('.filter-industry-checkbox[value="' + industry + '"]').prop('checked', true);
    });

    selectedFields.forEach(function(sort_field) {
        $('.filter-field-checkbox[value="' + sort_field + '"]').prop('checked', true);
    });

    selectedSort.forEach(function(sort) {
        $('.filter-sort-checkbox[value="' + sort + '"]').prop('checked', true);
    });

    // Toggle the visibility of dropdown
    $('.checkbox-dropdown label').click(function () {
        dropdown.toggle();
    });

    // Change listener for checkboxes
    $('.filter-round-checkbox').change(function () {
        updateFilter();
    });

    $('.filter-industry-checkbox').change(function () {
        updateFilter();
    });

    $('.filter-field-checkbox').change(function () {
        $('.filter-field-checkbox').not(this).prop('checked', false);
        updateFilter();
    });

    $('.filter-sort-checkbox').change(function () {
        $('.filter-sort-checkbox').not(this).prop('checked', false);
        updateFilter();
    });

    function updateFilter() {
        var selectedRounds = $('.filter-round-checkbox:checked').map(function () {
            return $(this).val();
        }).get();

        var selectedIndustries = $('.filter-industry-checkbox:checked').map(function () {
            return $(this).val();
        }).get();

        var selectedFields = $('.filter-field-checkbox:checked').map(function () {
            return $(this).val();
        }).get();

        var selectedSort = $('.filter-sort-checkbox:checked').map(function () {
            return $(this).val();
        }).get();

        var queryParamsRound = selectedRounds.length > 0 ? 'round=' + selectedRounds.join('&round=') : '';
        var queryParamsIndustry = selectedIndustries.length > 0 ? 'industry=' + selectedIndustries.join('&industry=') : '';
        var queryParamsField = 'sort_field=' + selectedFields;
        var queryParamsSort = 'descending=' + selectedSort;


        var queryParams = [queryParamsRound, queryParamsIndustry, queryParamsField, queryParamsSort].filter(Boolean).join('&');

        var newUrl = window.location.pathname + (queryParams ? '?' + queryParams : '');
        history.replaceState(null, null, newUrl);

        $.get(window.location.href = newUrl);
    }
    });
