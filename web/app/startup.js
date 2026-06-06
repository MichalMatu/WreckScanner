refreshAdminStatus().finally(() => {
    updateLingeringCarsCounter();
    loadSavedWrecks();
    loadFieldPhotos();
});
document.addEventListener('langchange', updateLingeringCarsCounter);
