const industryCheckboxes = document.querySelectorAll('input[name="selected_industries"]');
const roundCheckboxes = document.querySelectorAll('input[name="selected_rounds"]');

function handleCheckboxClick(event) {
  const checkbox = event.target;
  const label = checkbox.parentElement;

  if (checkbox.checked) {
    label.classList.remove('border', 'border-black', 'cursor-pointer', 'transition-all', 'hover:bg-sky-500', 'hover:text-white', 'hover:border-sky-500');
    label.classList.add('bg-sky-500', 'text-white', 'border-none');
  } else {
    label.classList.remove('bg-sky-500', 'text-white', 'border-none');
    label.classList.add('border', 'border-black', 'cursor-pointer', 'transition-all', 'hover:bg-sky-500', 'hover:text-white', 'hover:border-sky-500');
  }
}

industryCheckboxes.forEach((checkbox) => {
  checkbox.addEventListener('click', handleCheckboxClick);
});

roundCheckboxes.forEach((checkbox) => {
  checkbox.addEventListener('click', handleCheckboxClick);
});
