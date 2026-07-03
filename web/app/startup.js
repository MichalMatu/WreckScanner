refreshAdminStatus().finally(() => {
    loadFieldPhotos();
});
document.addEventListener('langchange', updateLayerCounters);
