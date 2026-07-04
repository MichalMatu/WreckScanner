function filePickerSummaryText(count) {
    if (!count) return t('filePicker.empty');
    if (count === 1) return t('filePicker.selectedOne');
    return t('filePicker.selectedMany', { n: count });
}

function updateFilePickerSummary(input) {
    if (!input?.id) return;
    const summary = document.querySelector(`.file-picker-summary[data-file-summary-for="${input.id}"]`);
    if (!summary) return;
    const count = input.files?.length || 0;
    summary.textContent = filePickerSummaryText(count);
    summary.classList.toggle('is-empty', count === 0);
}

function updateAllFilePickerSummaries() {
    document.querySelectorAll('.file-picker-input').forEach(updateFilePickerSummary);
}

document.querySelectorAll('.file-picker-input').forEach(input => {
    input.addEventListener('change', () => updateFilePickerSummary(input));
});
document.addEventListener('langchange', updateAllFilePickerSummaries);
updateAllFilePickerSummaries();
