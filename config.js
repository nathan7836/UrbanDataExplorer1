(function () {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = params.get('api');
    window.API_BASE_URL = fromQuery || 'http://localhost:8001';
})();
