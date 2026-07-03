refreshAdminStatus().finally(() => {
    updateLayerCounters();
    loadSavedWrecks();
    loadFieldPhotos();
});
document.addEventListener('langchange', updateLayerCounters);
